"""
backend/phase3_graph/graph_builder.py
======================================
PathMakers — NetworkX DAG Builder (Track K)

OWNER : K (Team Lead)
BRANCH: feature/k-graph-engine

CONTRACT
--------
Input  : RankedCandidateList   — produced by backend/phase2_matching/matcher.py
Output : RoadmapGraphResponse  — consumed by POST /api/roadmap/generate
                                  and rendered by @xyflow/react on the frontend

All type references are derived exclusively from contracts/schemas.py.
No fields are invented; no assumptions are made about upstream data.

ALGORITHM OVERVIEW
------------------
1.  Build a node-id set from the candidate list for O(1) lookup.
2.  For every candidate, add a DiGraph node keyed by course_id.
3.  For every prereq_id in candidate.prereq_ids:
      - If the prereq exists in the candidate set  → add directed edge
      - If the prereq is NOT in the candidate set  → orphan-prune (skip silently,
        log a warning). Never add an edge to an unknown node.
4.  Assert DAG invariant via nx.is_directed_acyclic_graph().
    If a cycle is detected raise GraphCycleError with the offending cycle.
5.  Compute topological depth for each node using a BFS from root nodes
    (in-degree == 0). Nodes at the same depth share the same x-column.
6.  Assign visual coordinates:
        x = depth * X_SPACING   (default 300 px)
        y = index_within_depth_layer * Y_SPACING  (default 170 px)
7.  Build RoadmapNode / RoadmapEdge lists in topological order.
8.  Return RoadmapGraphResponse.
"""

from __future__ import annotations

import logging
from collections import deque
from datetime import datetime, timezone

import networkx as nx

from contracts.schemas import (
    DifficultyLevel,
    EdgeType,
    NodeStatus,
    RankedCandidateList,
    RankedCourse,
    RoadmapEdge,
    RoadmapGraphResponse,
    RoadmapNode,
    RoadmapNodeData,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Layout constants  (React Flow pixel units)
# ---------------------------------------------------------------------------

X_SPACING: int = 300   # horizontal gap between depth layers
Y_SPACING: int = 170   # vertical gap between nodes in the same layer


# ---------------------------------------------------------------------------
# Custom exception — caught by the FastAPI route and returned as HTTP 422
# ---------------------------------------------------------------------------

class GraphCycleError(ValueError):
    """
    Raised when the candidate prereq_ids form a directed cycle.
    Carries the offending cycle as a list of course_ids for debugging.
    """

    def __init__(self, cycle: list[str]) -> None:
        self.cycle = cycle
        super().__init__(
            f"Cycle detected in prerequisite graph: {' -> '.join(cycle)}"
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_digraph(
    candidates: list[RankedCourse],
    known_ids: set[str],
) -> nx.DiGraph:
    """
    Construct a directed graph from the candidate list.

    Orphan guard: any prereq_id not present in known_ids is silently
    pruned and logged. This keeps the graph self-consistent regardless
    of whether courses.csv carries a prereq_ids column.
    """
    G: nx.DiGraph = nx.DiGraph()

    # Add all nodes first so edges can reference them safely
    for course in candidates:
        G.add_node(course.course_id, course=course)

    # Add edges — orphan-prune unknown prereqs
    for course in candidates:
        for prereq_id in course.prereq_ids:
            if prereq_id not in known_ids:
                logger.warning(
                    "Orphan prereq pruned: course '%s' references '%s' "
                    "which is not in the candidate set.",
                    course.course_id,
                    prereq_id,
                )
                continue
            # Edge direction: prerequisite → dependent
            G.add_edge(prereq_id, course.course_id)

    return G


def _assert_acyclic(G: nx.DiGraph) -> None:
    """
    Raise GraphCycleError if G contains a directed cycle.
    Uses nx.find_cycle for a concrete cycle path in the error message.
    """
    if not nx.is_directed_acyclic_graph(G):
        try:
            raw_cycle = nx.find_cycle(G, orientation="original")
            # raw_cycle is list of (u, v, direction) tuples
            cycle_nodes = [edge[0] for edge in raw_cycle]
            cycle_nodes.append(raw_cycle[-1][1])  # close the loop
        except nx.NetworkXNoCycle:
            cycle_nodes = ["<unknown>"]
        raise GraphCycleError(cycle_nodes)


def _compute_depths(G: nx.DiGraph, topo_order: list[str]) -> dict[str, int]:
    """
    BFS from all root nodes (in-degree == 0) to assign a depth level
    to every node. Depth = length of the longest path from any root.

    Using longest-path depth (not shortest) ensures that nodes requiring
    multiple prerequisites are placed after all their parents are visible.
    """
    depth: dict[str, int] = {node: 0 for node in G.nodes}

    # Process nodes in topological order — guarantees all predecessors
    # are already assigned a depth before the current node is visited.
    for node in topo_order:
        for predecessor in G.predecessors(node):
            depth[node] = max(depth[node], depth[predecessor] + 1)

    return depth


def _assign_positions(
    topo_order: list[str],
    depth: dict[str, int],
) -> dict[str, dict[str, float]]:
    """
    Compute {course_id: {"x": float, "y": float}} for every node.

    Layout:
        x = depth * X_SPACING
        y = index_within_depth_layer * Y_SPACING

    Nodes within the same depth layer are ordered by their position
    in the topological sort (higher ML score = earlier in topo order
    because Phase 2 sorts by score descending).
    """
    # Group nodes by depth layer in topological order
    layers: dict[int, list[str]] = {}
    for node in topo_order:
        d = depth[node]
        layers.setdefault(d, []).append(node)

    positions: dict[str, dict[str, float]] = {}
    for d, nodes_at_depth in layers.items():
        for idx, node in enumerate(nodes_at_depth):
            positions[node] = {
                "x": float(d * X_SPACING),
                "y": float(idx * Y_SPACING),
            }

    return positions


def _build_node(
    course: RankedCourse,
    position: dict[str, float],
    in_degree: int,
) -> RoadmapNode:
    """
    Construct a RoadmapNode from a RankedCourse.

    is_unlocked = True  iff in_degree == 0 (root node — no prerequisites).
    All nodes start with status = PENDING.
    """
    data = RoadmapNodeData(
        course_id=course.course_id,
        title=course.title,
        platform=course.platform,
        difficulty=course.difficulty,
        duration_hours=course.duration_hours,
        skill_tags=course.skill_tags,
        score=course.score,
        shap_values=course.shap_values,
        explanation_text=course.explanation_text,
        url=course.url,
        status=NodeStatus.PENDING,
        is_unlocked=(in_degree == 0),
    )
    return RoadmapNode(
        id=course.course_id,
        type="courseNode",
        position=position,
        data=data,
    )


def _build_edge(source: str, target: str) -> RoadmapEdge:
    """
    Construct a RoadmapEdge for a prerequisite relationship.
    id convention: '{source}__{target}'
    """
    return RoadmapEdge(
        id=f"{source}__{target}",
        source=source,
        target=target,
        type=EdgeType.PREREQUISITE,
        animated=False,
        label="",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_graph(candidates: RankedCandidateList) -> RoadmapGraphResponse:
    """
    Build a prerequisite-aware DAG roadmap from a ranked candidate list.

    Parameters
    ----------
    candidates : RankedCandidateList
        Produced by backend/phase2_matching/matcher.py.
        Every RankedCourse.prereq_ids entry must reference a course_id
        that also appears in candidates.candidates (enforced by the
        orphan guard — unknown prereqs are pruned, not rejected).

    Returns
    -------
    RoadmapGraphResponse
        React Flow-compatible graph with nodes, edges, topological order,
        total hours, and UTC timestamp.

    Raises
    ------
    GraphCycleError
        If the prereq_ids form a directed cycle.  Callers should catch
        this and return HTTP 422 with the cycle payload.

    Notes
    -----
    Empty candidate list is valid input — returns an empty graph
    (nodes=[], edges=[]) without raising.
    """
    # ------------------------------------------------------------------
    # Empty graph guard
    # ------------------------------------------------------------------
    if not candidates.candidates:
        logger.info(
            "build_graph called with empty candidate list for learner '%s'. "
            "Returning empty RoadmapGraphResponse.",
            candidates.learner_id,
        )
        return RoadmapGraphResponse(
            learner_id=candidates.learner_id,
            target_role=candidates.target_role,
            nodes=[],
            edges=[],
            topological_order=[],
            total_hours=0.0,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    # ------------------------------------------------------------------
    # Build the directed graph
    # ------------------------------------------------------------------
    known_ids: set[str] = {c.course_id for c in candidates.candidates}
    course_map: dict[str, RankedCourse] = {
        c.course_id: c for c in candidates.candidates
    }

    G = _build_digraph(candidates.candidates, known_ids)

    # ------------------------------------------------------------------
    # Cycle detection
    # ------------------------------------------------------------------
    _assert_acyclic(G)

    # ------------------------------------------------------------------
    # Topological sort
    # ------------------------------------------------------------------
    topo_order: list[str] = list(nx.topological_sort(G))

    # ------------------------------------------------------------------
    # Depth + layout
    # ------------------------------------------------------------------
    depth = _compute_depths(G, topo_order)
    positions = _assign_positions(topo_order, depth)

    # ------------------------------------------------------------------
    # Assemble nodes (in topological order)
    # ------------------------------------------------------------------
    nodes: list[RoadmapNode] = []
    for course_id in topo_order:
        course = course_map[course_id]
        node = _build_node(
            course=course,
            position=positions[course_id],
            in_degree=G.in_degree(course_id),
        )
        nodes.append(node)

    # ------------------------------------------------------------------
    # Assemble edges (deduplicated, in topological source order)
    # ------------------------------------------------------------------
    edges: list[RoadmapEdge] = []
    seen_edges: set[str] = set()
    for source, target in G.edges():
        edge_id = f"{source}__{target}"
        if edge_id not in seen_edges:
            edges.append(_build_edge(source, target))
            seen_edges.add(edge_id)

    # ------------------------------------------------------------------
    # Totals
    # ------------------------------------------------------------------
    total_hours = sum(c.duration_hours for c in candidates.candidates)

    logger.info(
        "build_graph complete — learner='%s' role='%s' "
        "nodes=%d edges=%d total_hours=%.1f",
        candidates.learner_id,
        candidates.target_role,
        len(nodes),
        len(edges),
        total_hours,
    )

    return RoadmapGraphResponse(
        learner_id=candidates.learner_id,
        target_role=candidates.target_role,
        nodes=nodes,
        edges=edges,
        topological_order=topo_order,
        total_hours=total_hours,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
