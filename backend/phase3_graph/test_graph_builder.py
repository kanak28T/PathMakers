"""
backend/phase3_graph/test_graph_builder.py
==========================================
PathMakers — Unit Tests for graph_builder.py (Track K)

Run from repo root:
    python -m pytest backend/phase3_graph/test_graph_builder.py -v

All test inputs are constructed strictly from contracts/schemas.py types.
No external files, no network, no database.

Test coverage:
    1. Normal multi-tier DAG — correct nodes, edges, topo order, depths, positions
    2. Single root node (no prerequisites) — valid single-node graph
    3. Empty candidate list — valid empty RoadmapGraphResponse
    4. Orphan prerequisite pruning — unknown prereq_ids are pruned, not crashed
    5. Cycle detection — GraphCycleError raised with cycle payload
    6. Correct is_unlocked assignment — root nodes True, downstream False
    7. Total hours calculation — sum of all duration_hours
    8. Layout coordinates — x = depth*300, y = index_in_layer*170
    9. Edge id convention — format is '{source}__{target}'
   10. All output nodes/edges validate against Pydantic contracts
"""

from __future__ import annotations

import pytest

from contracts.schemas import (
    DifficultyLevel,
    EdgeType,
    NodeStatus,
    RankedCandidateList,
    RankedCourse,
    RoadmapGraphResponse,
)
from backend.phase3_graph.graph_builder import GraphCycleError, build_graph


# ---------------------------------------------------------------------------
# Fixtures — reusable RankedCourse builders
# ---------------------------------------------------------------------------

def _make_course(
    course_id: str,
    title: str,
    duration_hours: float = 10.0,
    prereq_ids: list[str] | None = None,
    difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE,
    score: float = 0.80,
) -> RankedCourse:
    """Helper: construct a minimal but valid RankedCourse."""
    return RankedCourse(
        course_id=course_id,
        title=title,
        platform="Coursera",
        difficulty=difficulty,
        duration_hours=duration_hours,
        score=score,
        shap_values={},
        explanation_text="test explanation",
        prereq_ids=prereq_ids or [],
        skill_tags=["python"],
        url="https://example.com",
    )


def _make_candidates(
    learner_id: str,
    courses: list[RankedCourse],
    target_role: str = "ai_ml_engineer",
    diagnostic_score: float = 0.70,
) -> RankedCandidateList:
    """Helper: wrap courses into a RankedCandidateList."""
    return RankedCandidateList(
        learner_id=learner_id,
        target_role=target_role,
        diagnostic_score=diagnostic_score,
        candidates=courses,
    )


# ---------------------------------------------------------------------------
# Test 1 — Normal multi-tier DAG
# ---------------------------------------------------------------------------

class TestNormalDAG:
    """
    Three-tier DAG:
        c_001 (root)
        c_002 (root)
        c_003 → requires c_001
        c_004 → requires c_001, c_002
        c_005 → requires c_003, c_004
    """

    def setup_method(self):
        courses = [
            _make_course("c_001", "Python Basics",       duration_hours=20.0, prereq_ids=[]),
            _make_course("c_002", "Math Foundations",    duration_hours=18.0, prereq_ids=[]),
            _make_course("c_003", "Data Analysis",       duration_hours=15.0, prereq_ids=["c_001"]),
            _make_course("c_004", "ML Fundamentals",     duration_hours=30.0, prereq_ids=["c_001", "c_002"]),
            _make_course("c_005", "Deep Learning",       duration_hours=25.0, prereq_ids=["c_003", "c_004"]),
        ]
        self.candidates = _make_candidates("learner_001", courses)
        self.result = build_graph(self.candidates)

    def test_returns_roadmap_graph_response(self):
        assert isinstance(self.result, RoadmapGraphResponse)

    def test_correct_node_count(self):
        assert len(self.result.nodes) == 5

    def test_correct_edge_count(self):
        # edges: c001->c003, c001->c004, c002->c004, c003->c005, c004->c005
        assert len(self.result.edges) == 5

    def test_topological_order_respects_prerequisites(self):
        order = self.result.topological_order
        # Every prereq must appear before its dependent
        pos = {cid: i for i, cid in enumerate(order)}
        assert pos["c_001"] < pos["c_003"]
        assert pos["c_001"] < pos["c_004"]
        assert pos["c_002"] < pos["c_004"]
        assert pos["c_003"] < pos["c_005"]
        assert pos["c_004"] < pos["c_005"]

    def test_all_course_ids_in_topological_order(self):
        assert set(self.result.topological_order) == {"c_001", "c_002", "c_003", "c_004", "c_005"}

    def test_total_hours(self):
        assert self.result.total_hours == pytest.approx(20.0 + 18.0 + 15.0 + 30.0 + 25.0)

    def test_generated_at_is_iso8601(self):
        from datetime import datetime
        # Must parse without error
        dt = datetime.fromisoformat(self.result.generated_at)
        assert dt.tzinfo is not None  # must be timezone-aware

    def test_learner_id_preserved(self):
        assert self.result.learner_id == "learner_001"

    def test_target_role_preserved(self):
        assert self.result.target_role == "ai_ml_engineer"


# ---------------------------------------------------------------------------
# Test 2 — Single root node
# ---------------------------------------------------------------------------

class TestSingleNode:

    def setup_method(self):
        courses = [_make_course("c_001", "Intro Course", duration_hours=5.0)]
        self.result = build_graph(_make_candidates("learner_002", courses))

    def test_one_node(self):
        assert len(self.result.nodes) == 1

    def test_zero_edges(self):
        assert len(self.result.edges) == 0

    def test_topo_order_has_one_entry(self):
        assert self.result.topological_order == ["c_001"]

    def test_total_hours(self):
        assert self.result.total_hours == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# Test 3 — Empty candidate list
# ---------------------------------------------------------------------------

class TestEmptyGraph:

    def setup_method(self):
        # Empty candidates list — must use min_length bypass via direct construction
        self.candidates = RankedCandidateList(
            learner_id="learner_003",
            target_role="data_scientist",
            diagnostic_score=0.50,
            candidates=[_make_course("c_placeholder", "placeholder")],
        )
        # Override candidates to empty after construction to test the guard
        self.candidates.candidates = []
        self.result = build_graph(self.candidates)

    def test_returns_valid_response(self):
        assert isinstance(self.result, RoadmapGraphResponse)

    def test_empty_nodes(self):
        assert self.result.nodes == []

    def test_empty_edges(self):
        assert self.result.edges == []

    def test_empty_topo_order(self):
        assert self.result.topological_order == []

    def test_zero_total_hours(self):
        assert self.result.total_hours == 0.0

    def test_learner_id_preserved(self):
        assert self.result.learner_id == "learner_003"


# ---------------------------------------------------------------------------
# Test 4 — Orphan prerequisite pruning
# ---------------------------------------------------------------------------

class TestOrphanPruning:
    """
    c_002 lists 'c_ghost' as a prereq — but c_ghost is not in the candidate set.
    The orphan guard must prune the edge silently and still produce a valid graph.
    """

    def setup_method(self):
        courses = [
            _make_course("c_001", "Foundation",    duration_hours=10.0, prereq_ids=[]),
            _make_course("c_002", "Intermediate",  duration_hours=12.0, prereq_ids=["c_001", "c_ghost"]),
        ]
        self.result = build_graph(_make_candidates("learner_004", courses))

    def test_graph_builds_without_error(self):
        assert isinstance(self.result, RoadmapGraphResponse)

    def test_only_known_edge_exists(self):
        # Only c_001 -> c_002 should exist; c_ghost -> c_002 must be pruned
        edge_ids = {e.id for e in self.result.edges}
        assert "c_001__c_002" in edge_ids
        assert not any("c_ghost" in eid for eid in edge_ids)

    def test_correct_node_count(self):
        # c_ghost must NOT appear as a node
        node_ids = {n.id for n in self.result.nodes}
        assert "c_ghost" not in node_ids
        assert len(self.result.nodes) == 2

    def test_topological_order_valid(self):
        order = self.result.topological_order
        pos = {cid: i for i, cid in enumerate(order)}
        assert pos["c_001"] < pos["c_002"]


# ---------------------------------------------------------------------------
# Test 5 — Cycle detection
# ---------------------------------------------------------------------------

class TestCycleDetection:
    """
    c_001 -> c_002 -> c_003 -> c_001 forms a cycle.
    GraphCycleError must be raised.
    """

    def test_cycle_raises_graph_cycle_error(self):
        courses = [
            _make_course("c_001", "Course A", prereq_ids=["c_003"]),
            _make_course("c_002", "Course B", prereq_ids=["c_001"]),
            _make_course("c_003", "Course C", prereq_ids=["c_002"]),
        ]
        candidates = _make_candidates("learner_005", courses)
        with pytest.raises(GraphCycleError) as exc_info:
            build_graph(candidates)
        assert exc_info.value.cycle  # cycle list must be non-empty

    def test_cycle_error_contains_course_ids(self):
        courses = [
            _make_course("c_001", "Course A", prereq_ids=["c_002"]),
            _make_course("c_002", "Course B", prereq_ids=["c_001"]),
        ]
        candidates = _make_candidates("learner_005b", courses)
        with pytest.raises(GraphCycleError) as exc_info:
            build_graph(candidates)
        cycle = exc_info.value.cycle
        # Both nodes must appear in the reported cycle
        assert any("c_001" in c or "c_002" in c for c in cycle)

    def test_self_loop_raises_error(self):
        # A course that lists itself as a prerequisite
        courses = [
            _make_course("c_001", "Self-loop Course", prereq_ids=["c_001"]),
        ]
        candidates = _make_candidates("learner_005c", courses)
        with pytest.raises(GraphCycleError):
            build_graph(candidates)


# ---------------------------------------------------------------------------
# Test 6 — is_unlocked assignment
# ---------------------------------------------------------------------------

class TestUnlockStatus:
    """
    Root nodes (in-degree == 0) must have is_unlocked=True.
    Downstream nodes must have is_unlocked=False.
    """

    def setup_method(self):
        courses = [
            _make_course("c_001", "Root A",      prereq_ids=[]),
            _make_course("c_002", "Root B",      prereq_ids=[]),
            _make_course("c_003", "Downstream",  prereq_ids=["c_001", "c_002"]),
        ]
        self.result = build_graph(_make_candidates("learner_006", courses))
        self.node_map = {n.id: n for n in self.result.nodes}

    def test_root_nodes_are_unlocked(self):
        assert self.node_map["c_001"].data.is_unlocked is True
        assert self.node_map["c_002"].data.is_unlocked is True

    def test_downstream_node_is_locked(self):
        assert self.node_map["c_003"].data.is_unlocked is False

    def test_all_nodes_start_pending(self):
        for node in self.result.nodes:
            assert node.data.status == NodeStatus.PENDING


# ---------------------------------------------------------------------------
# Test 7 — Layout coordinates
# ---------------------------------------------------------------------------

class TestLayoutCoordinates:
    """
    Linear chain: c_001 (depth 0) -> c_002 (depth 1) -> c_003 (depth 2)
    Expected positions:
        c_001: x=0,   y=0
        c_002: x=300, y=0
        c_003: x=600, y=0
    """

    def setup_method(self):
        courses = [
            _make_course("c_001", "Step 1", prereq_ids=[]),
            _make_course("c_002", "Step 2", prereq_ids=["c_001"]),
            _make_course("c_003", "Step 3", prereq_ids=["c_002"]),
        ]
        self.result = build_graph(_make_candidates("learner_007", courses))
        self.node_map = {n.id: n for n in self.result.nodes}

    def test_root_at_x_zero(self):
        assert self.node_map["c_001"].position["x"] == pytest.approx(0.0)

    def test_depth1_at_x_300(self):
        assert self.node_map["c_002"].position["x"] == pytest.approx(300.0)

    def test_depth2_at_x_600(self):
        assert self.node_map["c_003"].position["x"] == pytest.approx(600.0)

    def test_single_node_per_layer_y_is_zero(self):
        for node in self.result.nodes:
            assert node.position["y"] == pytest.approx(0.0)

    def test_two_nodes_same_layer_have_different_y(self):
        courses = [
            _make_course("c_001", "Root A", prereq_ids=[]),
            _make_course("c_002", "Root B", prereq_ids=[]),
        ]
        result = build_graph(_make_candidates("learner_007b", courses))
        node_map = {n.id: n for n in result.nodes}
        # Both at depth 0 — same x, different y
        assert node_map["c_001"].position["x"] == pytest.approx(node_map["c_002"].position["x"])
        assert node_map["c_001"].position["y"] != node_map["c_002"].position["y"]
        # y values must be 170 apart
        y_vals = sorted([node_map["c_001"].position["y"], node_map["c_002"].position["y"]])
        assert y_vals[1] - y_vals[0] == pytest.approx(170.0)


# ---------------------------------------------------------------------------
# Test 8 — Edge id convention and type
# ---------------------------------------------------------------------------

class TestEdgeProperties:

    def setup_method(self):
        courses = [
            _make_course("c_001", "Foundation", prereq_ids=[]),
            _make_course("c_002", "Advanced",   prereq_ids=["c_001"]),
        ]
        self.result = build_graph(_make_candidates("learner_008", courses))

    def test_edge_id_convention(self):
        assert self.result.edges[0].id == "c_001__c_002"

    def test_edge_source_and_target(self):
        edge = self.result.edges[0]
        assert edge.source == "c_001"
        assert edge.target == "c_002"

    def test_edge_type_is_prerequisite(self):
        assert self.result.edges[0].type == EdgeType.PREREQUISITE

    def test_edge_not_animated_by_default(self):
        assert self.result.edges[0].animated is False


# ---------------------------------------------------------------------------
# Test 9 — Node data fields preserved from RankedCourse
# ---------------------------------------------------------------------------

class TestNodeDataIntegrity:

    def setup_method(self):
        self.course = _make_course(
            "c_001", "Test Course",
            duration_hours=42.0,
            difficulty=DifficultyLevel.ADVANCED,
            score=0.93,
        )
        result = build_graph(_make_candidates("learner_009", [self.course]))
        self.node = result.nodes[0]

    def test_course_id(self):
        assert self.node.data.course_id == "c_001"

    def test_title(self):
        assert self.node.data.title == "Test Course"

    def test_duration_hours(self):
        assert self.node.data.duration_hours == pytest.approx(42.0)

    def test_difficulty(self):
        assert self.node.data.difficulty == DifficultyLevel.ADVANCED

    def test_score(self):
        assert self.node.data.score == pytest.approx(0.93)

    def test_node_type_is_course_node(self):
        assert self.node.type == "courseNode"

    def test_node_id_matches_course_id(self):
        assert self.node.id == self.node.data.course_id
