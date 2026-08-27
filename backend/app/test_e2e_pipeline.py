"""
backend/app/test_e2e_pipeline.py
=================================
PathMakers — End-to-End Integration Test: POST /api/roadmap/generate

Tests the real pipeline:
    DiagnosticResult → build_ranked_candidates() → build_graph()
    → RoadmapGraphResponse

Run from repo root:
    python -m pytest backend/app/test_e2e_pipeline.py -v

Requirements:
    - data/courses.csv, data/career_taxonomy.json, data/skill_aliases.csv on disk
    - All three are present after the merged PRs from R

Note: model.pkl is NOT required for this test.
score.py falls back to the deterministic heuristic stub automatically
when model.pkl is absent, so this test runs clean on any developer machine
without needing to train the model first.
"""

from __future__ import annotations

import pytest

from contracts.schemas import (
    DiagnosticResult,
    DifficultyLevel,
    EdgeType,
    NodeStatus,
    QuestionResponse,
    RoadmapGraphResponse,
)
from backend.phase2_matching.matcher import build_ranked_candidates
from backend.phase3_graph.graph_builder import build_graph


# ---------------------------------------------------------------------------
# Shared DiagnosticResult fixtures
# ---------------------------------------------------------------------------

def _make_diagnostic(
    learner_id: str = "e2e_learner_001",
    target_role: str = "computer_systems_analyst",
    confirmed: list[str] | None = None,
    weak: list[str] | None = None,
    overall_score: float = 0.60,
) -> DiagnosticResult:
    """Build a minimal but valid DiagnosticResult for e2e tests."""
    return DiagnosticResult(
        learner_id=learner_id,
        target_role=target_role,
        confirmed_skills=confirmed or ["active listening", "reading comprehension"],
        weak_skills=weak or ["programming", "systems analysis", "mathematics"],
        overall_score=overall_score,
        tier_breakdown={
            "beginner": 0.80,
            "intermediate": 0.55,
            "advanced": 0.30,
        },
        responses=[],
    )


# ---------------------------------------------------------------------------
# Test 1 — Full pipeline returns a valid RoadmapGraphResponse
# ---------------------------------------------------------------------------

class TestFullPipeline:

    def setup_method(self):
        self.diagnostic = _make_diagnostic()
        self.ranked = build_ranked_candidates(self.diagnostic)
        self.graph = build_graph(self.ranked)

    def test_returns_roadmap_graph_response(self):
        assert isinstance(self.graph, RoadmapGraphResponse)

    def test_learner_id_preserved_end_to_end(self):
        assert self.graph.learner_id == "e2e_learner_001"

    def test_graph_has_at_least_one_node(self):
        assert len(self.graph.nodes) >= 1

    def test_topological_order_matches_node_count(self):
        assert len(self.graph.topological_order) == len(self.graph.nodes)

    def test_all_node_ids_in_topological_order(self):
        node_ids = {n.id for n in self.graph.nodes}
        topo_ids = set(self.graph.topological_order)
        assert node_ids == topo_ids

    def test_total_hours_is_positive(self):
        assert self.graph.total_hours > 0.0

    def test_generated_at_is_set(self):
        assert self.graph.generated_at
        from datetime import datetime
        dt = datetime.fromisoformat(self.graph.generated_at)
        assert dt.tzinfo is not None

    def test_all_nodes_start_pending(self):
        for node in self.graph.nodes:
            assert node.data.status == NodeStatus.PENDING

    def test_all_nodes_have_valid_difficulty(self):
        valid = {d.value for d in DifficultyLevel}
        for node in self.graph.nodes:
            assert node.data.difficulty.value in valid

    def test_all_nodes_have_non_empty_title(self):
        for node in self.graph.nodes:
            assert node.data.title.strip()

    def test_all_edges_reference_existing_nodes(self):
        node_ids = {n.id for n in self.graph.nodes}
        for edge in self.graph.edges:
            assert edge.source in node_ids, f"Edge source {edge.source} not in nodes"
            assert edge.target in node_ids, f"Edge target {edge.target} not in nodes"

    def test_no_self_loop_edges(self):
        for edge in self.graph.edges:
            assert edge.source != edge.target

    def test_edge_ids_are_unique(self):
        edge_ids = [e.id for e in self.graph.edges]
        assert len(edge_ids) == len(set(edge_ids))

    def test_node_ids_are_unique(self):
        node_ids = [n.id for n in self.graph.nodes]
        assert len(node_ids) == len(set(node_ids))

    def test_root_nodes_are_unlocked(self):
        # Nodes with no incoming edges in the graph must be unlocked
        node_map = {n.id: n for n in self.graph.nodes}
        targets = {e.target for e in self.graph.edges}
        for node in self.graph.nodes:
            if node.id not in targets:
                assert node.data.is_unlocked is True, (
                    f"Root node {node.id} should be unlocked"
                )

    def test_downstream_nodes_are_locked(self):
        targets = {e.target for e in self.graph.edges}
        node_map = {n.id: n for n in self.graph.nodes}
        for node_id in targets:
            assert node_map[node_id].data.is_unlocked is False, (
                f"Downstream node {node_id} should be locked"
            )

    def test_all_node_positions_have_x_and_y(self):
        for node in self.graph.nodes:
            assert "x" in node.position
            assert "y" in node.position
            assert isinstance(node.position["x"], float)
            assert isinstance(node.position["y"], float)

    def test_node_type_is_coursenode(self):
        for node in self.graph.nodes:
            assert node.type == "courseNode"


# ---------------------------------------------------------------------------
# Test 2 — Matcher returns correct contract shape
# ---------------------------------------------------------------------------

class TestMatcherContract:

    def setup_method(self):
        self.diagnostic = _make_diagnostic(
            learner_id="e2e_learner_002",
            target_role="web_developer",
            confirmed=["reading comprehension", "active listening"],
            weak=["programming", "technology design"],
        )
        self.ranked = build_ranked_candidates(self.diagnostic)

    def test_ranked_candidate_list_is_valid(self):
        from contracts.schemas import RankedCandidateList
        assert isinstance(self.ranked, RankedCandidateList)

    def test_learner_id_preserved(self):
        assert self.ranked.learner_id == "e2e_learner_002"

    def test_has_candidates(self):
        assert len(self.ranked.candidates) >= 1

    def test_all_scores_in_range(self):
        for course in self.ranked.candidates:
            assert 0.0 <= course.score <= 1.0

    def test_all_candidates_have_title(self):
        for course in self.ranked.candidates:
            assert course.title.strip()

    def test_all_candidates_have_valid_difficulty(self):
        valid = {d.value for d in DifficultyLevel}
        for course in self.ranked.candidates:
            assert course.difficulty.value in valid

    def test_all_candidates_have_non_negative_duration(self):
        for course in self.ranked.candidates:
            assert course.duration_hours >= 0.0


# ---------------------------------------------------------------------------
# Test 3 — Different career targets produce different graphs
# ---------------------------------------------------------------------------

class TestCareerTargetIsolation:

    def test_different_targets_produce_different_roadmaps(self):
        d1 = _make_diagnostic(
            learner_id="e2e_learner_003a",
            target_role="computer_systems_analyst",
        )
        d2 = _make_diagnostic(
            learner_id="e2e_learner_003b",
            target_role="web_developer",
        )
        g1 = build_graph(build_ranked_candidates(d1))
        g2 = build_graph(build_ranked_candidates(d2))

        ids1 = {n.id for n in g1.nodes}
        ids2 = {n.id for n in g2.nodes}

        # The two career paths should not be identical
        assert ids1 != ids2


# ---------------------------------------------------------------------------
# Test 4 — High-skill learner gets a leaner roadmap
# ---------------------------------------------------------------------------

class TestHighSkillLearner:
    """
    A learner who has confirmed more skills should receive a roadmap
    with fewer or different courses than a learner starting from scratch.
    This validates that the matcher is sensitive to confirmed_skills.
    """

    def test_more_confirmed_skills_affects_ranking(self):
        novice = _make_diagnostic(
            learner_id="novice",
            target_role="computer_systems_analyst",
            confirmed=[],
            weak=["programming", "systems analysis", "mathematics",
                  "active listening", "reading comprehension"],
            overall_score=0.20,
        )
        expert = _make_diagnostic(
            learner_id="expert",
            target_role="computer_systems_analyst",
            confirmed=["programming", "systems analysis", "mathematics",
                       "active listening", "reading comprehension",
                       "critical thinking", "troubleshooting"],
            weak=[],
            overall_score=0.95,
        )
        g_novice = build_graph(build_ranked_candidates(novice))
        g_expert = build_graph(build_ranked_candidates(expert))

        # Both should produce valid responses
        assert isinstance(g_novice, RoadmapGraphResponse)
        assert isinstance(g_expert, RoadmapGraphResponse)

        # Their course sets should differ (different gap profiles)
        ids_novice = {n.id for n in g_novice.nodes}
        ids_expert = {n.id for n in g_expert.nodes}
        assert ids_novice != ids_expert
