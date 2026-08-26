"""
contracts/schemas.py
====================
PathMakers — Frozen Integration Contracts (Pydantic V2)

This file is the single source of truth for every inter-phase data boundary.
No team member may change a field name, type, or optionality without a group
sync through K (Team Lead).  All mock JSON files in this directory must
validate against the models defined here.

Boundary map:
  Phase 1 → Phase 2  :  DiagnosticResult
  Phase 2 → Phase 3  :  RankedCandidateList
  Phase 3 → Frontend :  RoadmapGraphResponse
  Phase 4 → Frontend :  RoadmapPatchEvent  (SSE payload)
  Phase 2 → ML       :  ScoringFeatures  →  ScoringResult
  Frontend → Phase 4 :  RecalibrateRequest
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared enumerations
# ---------------------------------------------------------------------------


class DifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class NodeStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PatchTrigger(str, Enum):
    QUIZ_FAILURE = "quiz_failure"
    MODULE_SKIP = "module_skip"
    QUIZ_PASS = "quiz_pass"
    MANUAL_RECALIBRATE = "manual_recalibrate"


class EdgeType(str, Enum):
    PREREQUISITE = "prerequisite"
    RECOMMENDED = "recommended"
    REMEDIATION = "remediation"


# ---------------------------------------------------------------------------
# Phase 1 — Learner intake & diagnostic scoring
# ---------------------------------------------------------------------------


class LearnerProfile(BaseModel):
    """Raw intake data collected from the onboarding form."""

    learner_id: str = Field(..., description="UUID assigned at session creation")
    name: str
    target_role: str = Field(
        ..., description="Career goal key matching career_taxonomy.json (e.g. 'ai_ml_engineer')"
    )
    self_reported_skills: list[str] = Field(
        default_factory=list,
        description="Skill tags the learner claims familiarity with",
    )
    experience_years: float = Field(
        0.0, ge=0.0, description="Total years of relevant professional experience"
    )


class QuestionResponse(BaseModel):
    """A single answered question from the diagnostic quiz."""

    question_id: str
    selected_option: str
    is_correct: bool
    difficulty: DifficultyLevel
    skill_tag: str = Field(..., description="Skill domain this question tests (e.g. 'python')")
    time_spent_seconds: int = Field(ge=0)


class DiagnosticResult(BaseModel):
    """
    Phase 1 → Phase 2 handoff.
    Produced by phase1_profiler, consumed by phase2_matching.
    """

    learner_id: str
    target_role: str
    confirmed_skills: list[str] = Field(
        ..., description="Skills where the learner passed the diagnostic gate"
    )
    weak_skills: list[str] = Field(
        ..., description="Skills where the learner failed or scored below threshold"
    )
    overall_score: float = Field(..., ge=0.0, le=1.0, description="Normalised diagnostic score")
    tier_breakdown: dict[str, float] = Field(
        ...,
        description="Score per difficulty tier: {'easy': 0.9, 'medium': 0.6, 'hard': 0.3}",
    )
    responses: list[QuestionResponse] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# ML scoring boundary
# ---------------------------------------------------------------------------


class ScoringFeatures(BaseModel):
    """
    Phase 2 → ML handoff.
    Passed to ml/score.py::score(). All fields are required; no defaults
    so callers cannot silently omit a feature.
    """

    course_id: str
    learner_id: str
    gap_severity: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Fraction of course skills absent from learner's confirmed_skills",
    )
    tag_similarity: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Jaccard similarity between course tags and target role requirements",
    )
    course_rating: float = Field(..., ge=0.0, le=5.0)
    difficulty_match: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="1.0 = perfect difficulty alignment with learner tier; 0.0 = severe mismatch",
    )
    prereq_satisfaction: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Fraction of course prerequisites already in confirmed_skills",
    )


class ScoringResult(BaseModel):
    """
    ML → Phase 2 return value.
    score.py must return this exact model.
    """

    course_id: str
    learner_id: str
    score: float = Field(..., ge=0.0, le=1.0, description="ML-predicted fit score (higher = better)")
    shap_values: dict[str, float] = Field(
        ...,
        description=(
            "Instance-level SHAP value per feature. "
            "Positive = pushed score up; Negative = pushed score down."
        ),
    )
    explanation_text: str = Field(
        ...,
        description="Human-readable XAI sentence generated from top SHAP contributors",
    )


# ---------------------------------------------------------------------------
# Phase 2 — Skill-gap matching & ML candidate ranking
# ---------------------------------------------------------------------------


class RankedCourse(BaseModel):
    """
    A single course candidate after ML scoring.
    Phase 2 → Phase 3 handoff element.
    """

    course_id: str
    title: str
    platform: str = Field(default="Coursera")
    difficulty: DifficultyLevel
    duration_hours: float = Field(ge=0.0)
    score: float = Field(..., ge=0.0, le=1.0, description="ML fit score from ScoringResult")
    shap_values: dict[str, float]
    explanation_text: str
    prereq_ids: list[str] = Field(
        default_factory=list,
        description="course_ids that must appear earlier in the DAG. All must exist in this list.",
    )
    skill_tags: list[str] = Field(default_factory=list)
    url: str = Field(default="")


class RankedCandidateList(BaseModel):
    """
    Phase 2 → Phase 3 handoff.
    Produced by phase2_matching, consumed by phase3_graph.
    INVARIANT: every course_id referenced in any prereq_ids list
    must also appear as a top-level course_id in this candidates list.
    """

    learner_id: str
    target_role: str
    diagnostic_score: float = Field(..., ge=0.0, le=1.0)
    candidates: list[RankedCourse] = Field(
        ..., min_length=1, description="Ordered list of courses to consider for the roadmap"
    )


# ---------------------------------------------------------------------------
# Phase 3 — DAG / Roadmap graph
# ---------------------------------------------------------------------------


class RoadmapNodeData(BaseModel):
    """React Flow node data payload — all UI-renderable fields live here."""

    course_id: str
    title: str
    platform: str
    difficulty: DifficultyLevel
    duration_hours: float
    skill_tags: list[str]
    score: float
    shap_values: dict[str, float]
    explanation_text: str
    url: str
    status: NodeStatus = NodeStatus.PENDING
    is_unlocked: bool = Field(
        default=False,
        description="True when all prerequisite nodes are COMPLETED",
    )


class RoadmapNode(BaseModel):
    """React Flow node envelope.  'id' == course_id for direct edge lookup."""

    id: str
    type: str = Field(default="courseNode", description="React Flow custom node type name")
    position: dict[str, float] = Field(
        ..., description="{'x': float, 'y': float} — layout coordinates"
    )
    data: RoadmapNodeData


class RoadmapEdge(BaseModel):
    """React Flow edge envelope."""

    id: str = Field(..., description="Convention: '{source}__{target}'")
    source: str = Field(..., description="course_id of prerequisite node")
    target: str = Field(..., description="course_id of dependent node")
    type: EdgeType = EdgeType.PREREQUISITE
    animated: bool = False
    label: str = Field(default="")


class RoadmapGraphResponse(BaseModel):
    """
    Phase 3 → Frontend handoff  (also served by /api/roadmap/mock).
    React Flow consumes nodes + edges directly.
    """

    learner_id: str
    target_role: str
    nodes: list[RoadmapNode]
    edges: list[RoadmapEdge]
    topological_order: list[str] = Field(
        ..., description="course_ids in valid topological traversal order"
    )
    total_hours: float = Field(..., description="Sum of duration_hours across all nodes")
    generated_at: str = Field(..., description="ISO-8601 UTC timestamp")


# ---------------------------------------------------------------------------
# Phase 4 — Dynamic recalibration
# ---------------------------------------------------------------------------


class RecalibrateRequest(BaseModel):
    """
    Frontend → Phase 4  (POST /api/roadmap/recalibrate).
    Sent when a user fails a quiz, skips a node, or manually requests re-routing.
    """

    learner_id: str
    trigger: PatchTrigger
    node_id: str = Field(..., description="course_id of the node that triggered recalibration")
    quiz_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Provided when trigger is QUIZ_FAILURE or QUIZ_PASS",
    )
    retry_count: int = Field(
        default=0,
        ge=0,
        description="Number of times this node has already triggered recalibration",
    )


class PatchedNode(BaseModel):
    """Describes a single node change within a graph patch."""

    id: str
    label: str
    status: NodeStatus
    position: dict[str, float] | None = None


class RoadmapPatchEvent(BaseModel):
    """
    Phase 4 → Frontend SSE payload.
    Streamed on the /api/roadmap/stream/{learner_id} endpoint.
    Frontend merges this diff into the existing React Flow state.

    IMPORTANT: The frontend must never replace the full graph on receipt
    of a patch event — it merges added/removed/updated deltas only.
    """

    event: str = Field(default="graph_patch", description="SSE event name, always 'graph_patch'")
    learner_id: str
    trigger: PatchTrigger
    added_nodes: list[PatchedNode] = Field(default_factory=list)
    removed_node_ids: list[str] = Field(default_factory=list)
    updated_nodes: list[PatchedNode] = Field(default_factory=list)
    added_edges: list[RoadmapEdge] = Field(default_factory=list)
    removed_edge_ids: list[str] = Field(default_factory=list)
    summary: str = Field(
        ...,
        description="Human-readable diff summary shown in the UI toast notification",
    )
    remediation_path: list[str] = Field(
        default_factory=list,
        description="Ordered course_ids of the new remediation sub-path, if any",
    )
    timestamp: str = Field(..., description="ISO-8601 UTC timestamp of the patch")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    db_mode: str = Field(default="WAL", description="SQLite journal mode")
    details: dict[str, Any] = Field(default_factory=dict)
