"""
backend/app/main.py
===================
PathMakers — FastAPI Application

OWNER: K (Team Lead / Person B)

ENDPOINTS:
  GET  /health                          -> HealthResponse
  GET  /api/roadmap/mock                -> RoadmapGraphResponse (mock, always available)
  GET  /api/roadmap/patch/mock          -> RoadmapPatchEvent   (mock, always available)
  POST /api/roadmap/generate            -> RoadmapGraphResponse (real pipeline: Phase 2 → Phase 3)
  POST /api/roadmap/recalibrate         -> RoadmapPatchEvent   (stub — Phase 4 wired Day 2)
  GET  /api/roadmap/stream/{learner_id} -> SSE stream           (stub — Phase 4 wired Day 2)
"""

from __future__ import annotations

import json
import sqlite3
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from contracts.schemas import (
    DiagnosticResult,
    HealthResponse,
    RankedCandidateList,
    RecalibrateRequest,
    RoadmapGraphResponse,
    RoadmapPatchEvent,
)
from backend.phase2_matching.matcher import build_ranked_candidates
from backend.phase3_graph.graph_builder import GraphCycleError, build_graph

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).resolve().parents[2]   # repo root
_CONTRACTS_DIR = _ROOT / "contracts"
_DB_PATH = _ROOT / "pathmakers.db"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


def _get_db_connection() -> sqlite3.Connection:
    """
    Open a SQLite connection in WAL mode.
    WAL mode allows concurrent readers and a single writer without locking.
    """
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.row_factory = sqlite3.Row
    return conn


def _init_db(conn: sqlite3.Connection) -> None:
    """Create tables if they do not exist.  Non-destructive on re-runs."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS learner_profiles (
            learner_id   TEXT PRIMARY KEY,
            target_role  TEXT NOT NULL,
            created_at   TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS diagnostic_results (
            learner_id      TEXT PRIMARY KEY,
            overall_score   REAL NOT NULL,
            confirmed_skills TEXT NOT NULL,  -- JSON array
            weak_skills      TEXT NOT NULL,  -- JSON array
            recorded_at      TEXT NOT NULL,
            FOREIGN KEY (learner_id) REFERENCES learner_profiles(learner_id)
        );

        CREATE TABLE IF NOT EXISTS roadmap_state (
            learner_id       TEXT PRIMARY KEY,
            graph_json       TEXT NOT NULL,  -- serialised RoadmapGraphResponse
            updated_at       TEXT NOT NULL,
            FOREIGN KEY (learner_id) REFERENCES learner_profiles(learner_id)
        );

        CREATE TABLE IF NOT EXISTS recalibration_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id   TEXT NOT NULL,
            trigger      TEXT NOT NULL,
            node_id      TEXT NOT NULL,
            patch_json   TEXT NOT NULL,  -- serialised RoadmapPatchEvent
            retry_count  INTEGER NOT NULL DEFAULT 0,
            logged_at    TEXT NOT NULL,
            FOREIGN KEY (learner_id) REFERENCES learner_profiles(learner_id)
        );
        """
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------------------------

# Module-level DB connection (single connection for this demo scope)
_db_conn: sqlite3.Connection | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise shared resources on startup; close cleanly on shutdown."""
    global _db_conn
    logger.info("PathMakers API starting up — initialising SQLite (WAL mode)…")
    _db_conn = _get_db_connection()
    _init_db(_db_conn)
    logger.info("Database ready at %s", _DB_PATH)
    yield
    if _db_conn:
        _db_conn.close()
        logger.info("Database connection closed.")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="PathMakers API",
    description="AI-powered personalised learning path recommender — backend service.",
    version="0.2.0-day1",
    lifespan=lifespan,
)

# CORS — allow the Next.js dev server and any localhost port during development
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
# Helper — load mock payloads from contracts/
# ---------------------------------------------------------------------------


def _load_mock(filename: str) -> dict:
    path = _CONTRACTS_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=500, detail=f"Mock file not found: {filename}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Strip internal _comment / _contract / _usage keys before returning
    return {k: v for k, v in data.items() if not k.startswith("_")}


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    """
    Returns API status, version, and SQLite journal mode.
    Useful as a quick sanity check from the frontend and CI.
    """
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
        },
    )


# ---------------------------------------------------------------------------
# Mock endpoints (Day 0 — stable contracts for Person R / frontend)
# ---------------------------------------------------------------------------


@app.get(
    "/api/roadmap/mock",
    response_model=RoadmapGraphResponse,
    tags=["Roadmap", "Mock"],
    summary="Return the canonical mock roadmap graph (AI/ML Engineer, 6 nodes)",
)
async def get_mock_roadmap() -> dict:
    """
    Serves the static mock_roadmap.json payload.
    Person R must build the React Flow canvas against this endpoint.
    This endpoint stays live even after real endpoints are wired.
    """
    return _load_mock("mock_roadmap.json")


@app.get(
    "/api/roadmap/patch/mock",
    response_model=RoadmapPatchEvent,
    tags=["Roadmap", "Mock"],
    summary="Return the canonical mock Phase 4 SSE diff payload",
)
async def get_mock_patch() -> dict:
    """
    Serves the static mock_patch.json payload.
    Person R must build the SSE listener and graph merge logic against this shape.
    Scenario: quiz failure at node c_004, remediation node c_007 inserted.
    """
    return _load_mock("mock_patch.json")


# ---------------------------------------------------------------------------
# Real endpoints — stubs (wired to phases in Days 1–3 by K)
# ---------------------------------------------------------------------------


@app.post(
    "/api/roadmap/generate",
    response_model=RoadmapGraphResponse,
    tags=["Roadmap"],
    summary="Generate a personalised roadmap from a diagnostic result",
)
async def generate_roadmap(diagnostic: DiagnosticResult) -> RoadmapGraphResponse:
    """
    Full pipeline: Phase 2 (matcher) → Phase 3 (graph builder).

    Phase 1 (profiler) runs on the client before this call —
    the DiagnosticResult it produces is passed directly here.

    Raises HTTP 422 if the candidate prereq_ids form a cycle.
    Raises HTTP 500 if the matcher finds no courses for the learner.
    """
    try:
        ranked: RankedCandidateList = build_ranked_candidates(diagnostic)
    except ValueError as exc:
        logger.error("Matcher error for learner %s: %s", diagnostic.learner_id, exc)
        raise HTTPException(status_code=500, detail=str(exc))

    try:
        graph: RoadmapGraphResponse = build_graph(ranked)
    except GraphCycleError as exc:
        logger.error("Cycle detected for learner %s: %s", diagnostic.learner_id, exc)
        raise HTTPException(
            status_code=422,
            detail={"error": "prerequisite_cycle", "cycle": exc.cycle},
        )

    logger.info(
        "generate_roadmap complete — learner=%s nodes=%d edges=%d",
        diagnostic.learner_id,
        len(graph.nodes),
        len(graph.edges),
    )
    return graph


@app.post(
    "/api/roadmap/recalibrate",
    response_model=RoadmapPatchEvent,
    tags=["Roadmap"],
    summary="Trigger dynamic recalibration on quiz failure or node skip",
)
async def recalibrate_roadmap(request: RecalibrateRequest) -> dict:
    """
    Day 0: Returns mock patch regardless of input.
    Day 2 (K): Wire to phase4_patch.recalibrator.compute_patch(request).

    Accepts a RecalibrateRequest (trigger event + node_id + retry_count).
    Returns a RoadmapPatchEvent for the frontend to merge into the graph.

    GUARD RAILS (K to implement in Day 4):
      - If retry_count >= 3, return a remediation path instead of failing node again.
      - Validate that node_id exists in the current roadmap_state for this learner.
    """
    # TODO (K, Day 2): Replace with real recalibration
    # from backend.phase4_patch.recalibrator import compute_patch
    # return compute_patch(request, _db_conn)
    logger.info(
        "recalibrate_roadmap called — learner=%s trigger=%s node=%s retry=%d [STUB]",
        request.learner_id,
        request.trigger,
        request.node_id,
        request.retry_count,
    )
    return _load_mock("mock_patch.json")


@app.get(
    "/api/roadmap/stream/{learner_id}",
    tags=["Roadmap", "SSE"],
    summary="SSE stream for real-time graph patch events",
)
async def stream_roadmap_patches(learner_id: str) -> StreamingResponse:
    """
    Server-Sent Events endpoint.  Frontend connects once and receives
    RoadmapPatchEvent objects as they are computed by Phase 4.

    Day 0: Sends a single mock patch event then keeps the connection alive.
    Day 2 (K): Replace with an async generator that yields real patch events
               from the recalibration engine via an asyncio.Queue.

    SSE message format:
        event: graph_patch
        data: <JSON-encoded RoadmapPatchEvent>

    Person R: connect with EventSource('/api/roadmap/stream/{learner_id}')
    and handle the 'graph_patch' event type.
    """

    async def _event_generator():
        # Day 0 stub: emit the mock patch once so R can test the SSE listener
        mock_patch = _load_mock("mock_patch.json")
        mock_patch["learner_id"] = learner_id  # personalise learner_id
        yield f"event: graph_patch\ndata: {json.dumps(mock_patch)}\n\n"

        # Keep the connection alive with periodic heartbeats
        # TODO (K, Day 2): Replace this loop with a real async event queue
        import asyncio  # noqa: PLC0415
        while True:
            await asyncio.sleep(30)
            yield ": heartbeat\n\n"  # SSE comment — keeps connection alive, no event fired

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable Nginx buffering
        },
    )
