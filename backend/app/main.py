"""
backend/app/main.py
===================
PathMakers — FastAPI Application (Integrated)

Full pipeline wired:
  POST /api/roadmap/generate
      LearnerProfile → Phase1 (score_diagnostic) → Phase2 (build_ranked_candidates)
      → Phase3 (build_graph) → RoadmapGraphResponse

  POST /api/roadmap/recalibrate
      RecalibrateRequest → Phase4 (compute_patch) → RoadmapPatchEvent

  GET  /api/roadmap/stream/{learner_id}
      SSE stream — real patches emitted; heartbeat keep-alive

Mock endpoints stay live for frontend development fallback.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from contracts.schemas import (
    DiagnosticResult,
    HealthResponse,
    LearnerProfile,
    RecalibrateRequest,
    RoadmapGraphResponse,
    RoadmapPatchEvent,
)

# ---------------------------------------------------------------------------
# Phase imports (wrapped in try/except so the mock layer still works if a
# phase module has an import error during development)
# ---------------------------------------------------------------------------
try:
    from backend.phase1_profiler.profiler import score_diagnostic
    _PHASE1_OK = True
except Exception as _e:
    _PHASE1_OK = False
    logging.getLogger(__name__).warning("Phase 1 import failed: %s", _e)

try:
    from backend.phase2_matching.matcher import build_ranked_candidates
    _PHASE2_OK = True
except Exception as _e:
    _PHASE2_OK = False
    logging.getLogger(__name__).warning("Phase 2 import failed: %s", _e)

try:
    from backend.phase3_graph.graph_builder import build_graph, GraphCycleError
    _PHASE3_OK = True
except Exception as _e:
    _PHASE3_OK = False
    logging.getLogger(__name__).warning("Phase 3 import failed: %s", _e)

try:
    from backend.phase4_patch.recalibrator import compute_patch
    _PHASE4_OK = True
except Exception as _e:
    _PHASE4_OK = False
    logging.getLogger(__name__).warning("Phase 4 import failed: %s", _e)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_ROOT          = Path(__file__).resolve().parents[2]
_CONTRACTS_DIR = _ROOT / "contracts"
_DB_PATH       = _ROOT / "pathmakers.db"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory SSE queues  {learner_id: asyncio.Queue}
# ---------------------------------------------------------------------------
_sse_queues: dict[str, asyncio.Queue] = {}


def _get_or_create_queue(learner_id: str) -> asyncio.Queue:
    if learner_id not in _sse_queues:
        _sse_queues[learner_id] = asyncio.Queue(maxsize=50)
    return _sse_queues[learner_id]


async def _push_patch(learner_id: str, patch: RoadmapPatchEvent) -> None:
    """Push a patch event to the learner's SSE queue (non-blocking)."""
    q = _get_or_create_queue(learner_id)
    try:
        q.put_nowait(patch.model_dump())
    except asyncio.QueueFull:
        logger.warning("SSE queue full for learner %s — dropping patch", learner_id)


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
def _get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.row_factory = sqlite3.Row
    return conn


def _init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS learner_profiles (
            learner_id   TEXT PRIMARY KEY,
            target_role  TEXT NOT NULL,
            created_at   TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS diagnostic_results (
            learner_id       TEXT PRIMARY KEY,
            overall_score    REAL NOT NULL,
            confirmed_skills TEXT NOT NULL,
            weak_skills      TEXT NOT NULL,
            recorded_at      TEXT NOT NULL,
            FOREIGN KEY (learner_id) REFERENCES learner_profiles(learner_id)
        );

        CREATE TABLE IF NOT EXISTS roadmap_state (
            learner_id  TEXT PRIMARY KEY,
            graph_json  TEXT NOT NULL,
            updated_at  TEXT NOT NULL,
            FOREIGN KEY (learner_id) REFERENCES learner_profiles(learner_id)
        );

        CREATE TABLE IF NOT EXISTS recalibration_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id  TEXT NOT NULL,
            trigger     TEXT NOT NULL,
            node_id     TEXT NOT NULL,
            patch_json  TEXT NOT NULL,
            retry_count INTEGER NOT NULL DEFAULT 0,
            logged_at   TEXT NOT NULL,
            FOREIGN KEY (learner_id) REFERENCES learner_profiles(learner_id)
        );
        """
    )
    conn.commit()


_db_conn: sqlite3.Connection | None = None


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _db_conn
    logger.info("PathMakers API starting — SQLite WAL mode")
    _db_conn = _get_db_connection()
    _init_db(_db_conn)
    logger.info("DB ready at %s", _DB_PATH)
    logger.info(
        "Phase status — P1:%s P2:%s P3:%s P4:%s",
        _PHASE1_OK, _PHASE2_OK, _PHASE3_OK, _PHASE4_OK,
    )
    yield
    if _db_conn:
        _db_conn.close()
        logger.info("DB connection closed.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="PathMakers API",
    description="AI-powered personalised learning path — full pipeline.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _load_mock(filename: str) -> dict:
    path = _CONTRACTS_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=500, detail=f"Mock file not found: {filename}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("_")}


def _save_profile(learner: LearnerProfile) -> None:
    if _db_conn is None:
        return
    try:
        _db_conn.execute(
            "INSERT OR REPLACE INTO learner_profiles (learner_id, target_role, created_at) "
            "VALUES (?, ?, ?)",
            (learner.learner_id, learner.target_role, datetime.now(timezone.utc).isoformat()),
        )
        _db_conn.commit()
    except Exception as exc:
        logger.warning("Failed to save learner profile: %s", exc)


def _save_roadmap(learner_id: str, graph: RoadmapGraphResponse) -> None:
    if _db_conn is None:
        return
    try:
        _db_conn.execute(
            "INSERT OR REPLACE INTO roadmap_state (learner_id, graph_json, updated_at) "
            "VALUES (?, ?, ?)",
            (learner_id, graph.model_dump_json(), datetime.now(timezone.utc).isoformat()),
        )
        _db_conn.commit()
    except Exception as exc:
        logger.warning("Failed to save roadmap state: %s", exc)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    db_mode = "WAL"
    if _db_conn:
        row = _db_conn.execute("PRAGMA journal_mode;").fetchone()
        db_mode = row[0].upper() if row else "UNKNOWN"
    return HealthResponse(
        status="ok",
        version=app.version,
        db_mode=db_mode,
        details={
            "db_path": str(_DB_PATH),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phases": {
                "phase1": _PHASE1_OK,
                "phase2": _PHASE2_OK,
                "phase3": _PHASE3_OK,
                "phase4": _PHASE4_OK,
            },
        },
    )


# ---------------------------------------------------------------------------
# Mock endpoints (always available — frontend fallback)
# ---------------------------------------------------------------------------
@app.get("/api/roadmap/mock", response_model=RoadmapGraphResponse, tags=["Mock"])
async def get_mock_roadmap() -> dict:
    return _load_mock("mock_roadmap.json")


@app.get("/api/roadmap/patch/mock", response_model=RoadmapPatchEvent, tags=["Mock"])
async def get_mock_patch() -> dict:
    return _load_mock("mock_patch.json")


# ---------------------------------------------------------------------------
# POST /api/roadmap/generate  — full Phase 1→2→3 pipeline
# ---------------------------------------------------------------------------
@app.post("/api/roadmap/generate", response_model=RoadmapGraphResponse, tags=["Roadmap"])
async def generate_roadmap(profile: LearnerProfile) -> dict:
    """
    Full pipeline:
      LearnerProfile → Phase1 diagnostic scoring → Phase2 ML ranking
      → Phase3 DAG builder → RoadmapGraphResponse

    Falls back to mock if any phase module failed to import.
    """
    logger.info("generate_roadmap — learner=%s role=%s", profile.learner_id, profile.target_role)

    # Persist profile
    _save_profile(profile)

    # ------------------------------------------------------------------
    # Phase 1 — build a DiagnosticResult from self-reported skills
    # (no quiz responses yet on first load — profile_learner handles empty)
    # ------------------------------------------------------------------
    if not (_PHASE1_OK and _PHASE2_OK and _PHASE3_OK):
        logger.warning("One or more phases unavailable — returning mock roadmap")
        return _load_mock("mock_roadmap.json")

    try:
        # Build a synthetic DiagnosticResult from the intake profile
        diagnostic = DiagnosticResult(
            learner_id=profile.learner_id,
            target_role=profile.target_role,
            confirmed_skills=profile.self_reported_skills,
            weak_skills=[],
            overall_score=min(0.5 + profile.experience_years * 0.05, 1.0),
            tier_breakdown={
                "beginner": 0.8 if profile.experience_years >= 1 else 0.5,
                "intermediate": 0.5 if profile.experience_years >= 2 else 0.3,
                "advanced": 0.3 if profile.experience_years >= 4 else 0.1,
            },
            responses=[],
        )

        # Phase 2 — rank courses
        ranked = build_ranked_candidates(diagnostic)

        # Phase 3 — build DAG
        graph = build_graph(ranked)

        # Persist roadmap
        _save_roadmap(profile.learner_id, graph)

        logger.info(
            "Roadmap generated — learner=%s nodes=%d edges=%d",
            profile.learner_id, len(graph.nodes), len(graph.edges),
        )
        return graph.model_dump()

    except GraphCycleError as exc:
        logger.error("Cycle in prerequisite graph: %s", exc.cycle)
        raise HTTPException(status_code=422, detail={"error": "cycle_detected", "cycle": exc.cycle})
    except ValueError as exc:
        logger.warning("Phase pipeline error: %s — falling back to mock", exc)
        return _load_mock("mock_roadmap.json")
    except Exception as exc:
        logger.exception("Unexpected error in generate_roadmap: %s", exc)
        return _load_mock("mock_roadmap.json")


# ---------------------------------------------------------------------------
# POST /api/roadmap/recalibrate  — Phase 4
# ---------------------------------------------------------------------------
@app.post("/api/roadmap/recalibrate", response_model=RoadmapPatchEvent, tags=["Roadmap"])
async def recalibrate_roadmap(request: RecalibrateRequest) -> dict:
    """
    Phase 4: compute a graph diff patch from a recalibration trigger.
    Pushes the patch to the learner's SSE queue for real-time delivery.
    Falls back to mock patch if Phase 4 module is unavailable.
    """
    logger.info(
        "recalibrate — learner=%s trigger=%s node=%s retry=%d",
        request.learner_id, request.trigger, request.node_id, request.retry_count,
    )

    if not _PHASE4_OK:
        return _load_mock("mock_patch.json")

    try:
        patch = compute_patch(request, _db_conn)
        # Push to SSE queue so stream endpoint delivers it live
        await _push_patch(request.learner_id, patch)
        return patch.model_dump()
    except Exception as exc:
        logger.exception("Phase 4 error: %s", exc)
        return _load_mock("mock_patch.json")


# ---------------------------------------------------------------------------
# GET /api/roadmap/stream/{learner_id}  — SSE
# ---------------------------------------------------------------------------
@app.get("/api/roadmap/stream/{learner_id}", tags=["SSE"])
async def stream_roadmap_patches(learner_id: str) -> StreamingResponse:
    """
    Server-Sent Events stream.
    Delivers RoadmapPatchEvent objects to the frontend in real time.
    Emits one mock patch on connect, then drains the learner's queue.
    """
    queue = _get_or_create_queue(learner_id)

    async def _generator():
        # Emit initial mock patch so frontend SSE listener can be tested immediately
        mock = _load_mock("mock_patch.json")
        mock["learner_id"] = learner_id
        yield f"event: graph_patch\ndata: {json.dumps(mock)}\n\n"

        while True:
            try:
                patch_dict = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield f"event: graph_patch\ndata: {json.dumps(patch_dict)}\n\n"
            except asyncio.TimeoutError:
                yield ": heartbeat\n\n"

    return StreamingResponse(
        _generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# POST /api/diagnostic/submit  — submit quiz answers → DiagnosticResult
# ---------------------------------------------------------------------------
@app.post("/api/diagnostic/submit", response_model=DiagnosticResult, tags=["Diagnostic"])
async def submit_diagnostic(
    learner_id: str,
    target_role: str,
    experience_years: float = 0.0,
    answers: list[dict] | None = None,
) -> dict:
    """
    Accept quiz answers from the frontend diagnostic modal.
    Returns a DiagnosticResult that can then be used to regenerate the roadmap.
    Falls back gracefully if Phase 1 is unavailable.
    """
    if not _PHASE1_OK or not answers:
        return DiagnosticResult(
            learner_id=learner_id,
            target_role=target_role,
            confirmed_skills=[],
            weak_skills=[],
            overall_score=0.5,
            tier_breakdown={"beginner": 0.5, "intermediate": 0.3, "advanced": 0.1},
            responses=[],
        ).model_dump()

    try:
        from backend.phase1_profiler.profiler import build_response, load_questions
        from contracts.schemas import LearnerProfile as LP, QuestionResponse

        questions_by_id = {q["question_id"]: q for q in load_questions()}
        responses: list[QuestionResponse] = []

        for ans in answers:
            qid = ans.get("question_id")
            if qid not in questions_by_id:
                continue
            resp = build_response(
                question=questions_by_id[qid],
                selected_option=ans.get("selected_option", "A"),
                time_spent_seconds=int(ans.get("time_spent_seconds", 0)),
            )
            responses.append(resp)

        learner = LP(
            learner_id=learner_id,
            name="",
            target_role=target_role,
            experience_years=experience_years,
        )
        result = score_diagnostic(learner, responses)

        if _db_conn:
            _db_conn.execute(
                "INSERT OR REPLACE INTO diagnostic_results "
                "(learner_id, overall_score, confirmed_skills, weak_skills, recorded_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    learner_id,
                    result.overall_score,
                    json.dumps(result.confirmed_skills),
                    json.dumps(result.weak_skills),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            _db_conn.commit()

        return result.model_dump()

    except Exception as exc:
        logger.exception("Diagnostic submit error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
