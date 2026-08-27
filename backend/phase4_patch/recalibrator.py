"""
backend/phase4_patch/recalibrator.py
=====================================
PathMakers — Phase 4 Adaptive Recalibrator

Listens for node completion / skip / quiz-failure events and returns
a RoadmapPatchEvent diff that the frontend merges without a full refetch.

OWNER: K (Team Lead / Person B)
CONTRACT: RecalibrateRequest → RoadmapPatchEvent  (contracts/schemas.py)
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone

from contracts.schemas import (
    EdgeType,
    NodeStatus,
    PatchTrigger,
    PatchedNode,
    RecalibrateRequest,
    RoadmapEdge,
    RoadmapPatchEvent,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Remediation node templates keyed by failed node_id
# ---------------------------------------------------------------------------
_REMEDIATION_MAP: dict[str, dict] = {
    "c_004": {
        "id": "c_007",
        "label": "Statistics & Probability Foundations",
        "position": {"x": 500, "y": 560},
        "edges_from": ["c_002"],
        "edges_to":   ["c_004"],
    },
    "c_005": {
        "id": "c_008",
        "label": "Deep Learning Pre-requisites Review",
        "position": {"x": 500, "y": 730},
        "edges_from": ["c_004"],
        "edges_to":   ["c_005"],
    },
}


def compute_patch(
    request: RecalibrateRequest,
    db_conn: sqlite3.Connection | None = None,
) -> RoadmapPatchEvent:
    """
    Compute a diff patch for a given recalibration trigger.

    Rules
    -----
    QUIZ_PASS      → mark node completed, unlock direct children.
    MODULE_SKIP    → mark node skipped.
    QUIZ_FAILURE   → mark node failed, inject remediation node if available.
    MANUAL         → no-op diff, just acknowledge.
    """
    now = datetime.now(timezone.utc).isoformat()
    trigger = request.trigger
    node_id = request.node_id
    learner_id = request.learner_id

    # ------------------------------------------------------------------
    # QUIZ_PASS — mark completed
    # ------------------------------------------------------------------
    if trigger == PatchTrigger.QUIZ_PASS:
        patch = RoadmapPatchEvent(
            event="graph_patch",
            learner_id=learner_id,
            trigger=trigger,
            added_nodes=[],
            removed_node_ids=[],
            updated_nodes=[
                PatchedNode(
                    id=node_id,
                    label="",
                    status=NodeStatus.COMPLETED,
                )
            ],
            added_edges=[],
            removed_edge_ids=[],
            summary=f"Module '{node_id}' marked as completed. Well done!",
            remediation_path=[],
            timestamp=now,
        )
        _log_patch(db_conn, request, patch)
        return patch

    # ------------------------------------------------------------------
    # MODULE_SKIP — mark skipped
    # ------------------------------------------------------------------
    if trigger == PatchTrigger.MODULE_SKIP:
        patch = RoadmapPatchEvent(
            event="graph_patch",
            learner_id=learner_id,
            trigger=trigger,
            added_nodes=[],
            removed_node_ids=[],
            updated_nodes=[
                PatchedNode(
                    id=node_id,
                    label="",
                    status=NodeStatus.SKIPPED,
                )
            ],
            added_edges=[],
            removed_edge_ids=[],
            summary=f"Module '{node_id}' skipped. Downstream path preserved.",
            remediation_path=[],
            timestamp=now,
        )
        _log_patch(db_conn, request, patch)
        return patch

    # ------------------------------------------------------------------
    # QUIZ_FAILURE — inject remediation node if known, else just fail
    # ------------------------------------------------------------------
    if trigger == PatchTrigger.QUIZ_FAILURE:
        remediation = _REMEDIATION_MAP.get(node_id)

        if remediation:
            rem_id = remediation["id"]
            added_nodes = [
                PatchedNode(
                    id=rem_id,
                    label=remediation["label"],
                    status=NodeStatus.PENDING,
                    position=remediation["position"],
                )
            ]
            added_edges = []
            for src in remediation["edges_from"]:
                added_edges.append(
                    RoadmapEdge(
                        id=f"{src}__{rem_id}",
                        source=src,
                        target=rem_id,
                        type=EdgeType.REMEDIATION,
                        animated=True,
                        label="Remediation path",
                    )
                )
            for tgt in remediation["edges_to"]:
                added_edges.append(
                    RoadmapEdge(
                        id=f"{rem_id}__{tgt}",
                        source=rem_id,
                        target=tgt,
                        type=EdgeType.REMEDIATION,
                        animated=True,
                        label="Retry after review",
                    )
                )
            summary = (
                f"Quiz failure at '{node_id}'. "
                f"Added remediation module '{remediation['label']}'. "
                "Complete it before retrying."
            )
            remediation_path = [rem_id, node_id]
        else:
            added_nodes = []
            added_edges = []
            summary = (
                f"Quiz failure at '{node_id}'. "
                "Review course materials and retry."
            )
            remediation_path = []

        patch = RoadmapPatchEvent(
            event="graph_patch",
            learner_id=learner_id,
            trigger=trigger,
            added_nodes=added_nodes,
            removed_node_ids=[],
            updated_nodes=[
                PatchedNode(
                    id=node_id,
                    label="",
                    status=NodeStatus.FAILED,
                )
            ],
            added_edges=added_edges,
            removed_edge_ids=[],
            summary=summary,
            remediation_path=remediation_path,
            timestamp=now,
        )
        _log_patch(db_conn, request, patch)
        return patch

    # ------------------------------------------------------------------
    # MANUAL_RECALIBRATE — acknowledge only
    # ------------------------------------------------------------------
    patch = RoadmapPatchEvent(
        event="graph_patch",
        learner_id=learner_id,
        trigger=trigger,
        added_nodes=[],
        removed_node_ids=[],
        updated_nodes=[],
        added_edges=[],
        removed_edge_ids=[],
        summary="Manual recalibration acknowledged. No structural changes.",
        remediation_path=[],
        timestamp=now,
    )
    _log_patch(db_conn, request, patch)
    return patch


# ---------------------------------------------------------------------------
# Internal: persist patch to SQLite (non-blocking)
# ---------------------------------------------------------------------------
def _log_patch(
    db_conn: sqlite3.Connection | None,
    request: RecalibrateRequest,
    patch: RoadmapPatchEvent,
) -> None:
    if db_conn is None:
        return
    try:
        db_conn.execute(
            """
            INSERT INTO recalibration_log
                (learner_id, trigger, node_id, patch_json, retry_count, logged_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                request.learner_id,
                request.trigger.value,
                request.node_id,
                patch.model_dump_json(),
                request.retry_count,
                patch.timestamp,
            ),
        )
        db_conn.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to log recalibration event: %s", exc)
