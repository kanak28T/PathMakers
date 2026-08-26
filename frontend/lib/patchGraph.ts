/**
 * lib/patchGraph.ts
 * Pure merge function: applies a RoadmapPatchEvent diff onto the current
 * React Flow nodes/edges arrays without a full graph refetch.
 *
 * This is the critical Phase 3→Frontend boundary rule:
 *   backend ships structure only, frontend owns coordinates.
 * Added nodes without a position in the patch fall back to a sensible default.
 */

import type { Node, Edge } from "@xyflow/react";
import type { RoadmapNodeData, RoadmapEdge, RoadmapPatchEvent } from "./types";

// @xyflow/react requires data to extend Record<string, unknown>
// RoadmapNodeData satisfies this constraint (see lib/types.ts)
type FlowNode = Node<RoadmapNodeData>;
type FlowEdge = Edge;

export function applyPatch(
  nodes: FlowNode[],
  edges: FlowEdge[],
  patch: RoadmapPatchEvent
): { nodes: FlowNode[]; edges: FlowEdge[] } {
  // ---- 1. Remove nodes ----
  let nextNodes = nodes.filter(
    (n) => !patch.removed_node_ids.includes(n.id)
  );

  // ---- 2. Update existing nodes ----
  nextNodes = nextNodes.map((n) => {
    const update = patch.updated_nodes.find((u) => u.id === n.id);
    if (!update) return n;
    return {
      ...n,
      position: update.position ?? n.position,
      data: {
        ...n.data,
        status: update.status,
        title: update.label || n.data.title,
      } as RoadmapNodeData,
    };
  });

  // ---- 3. Add new nodes ----
  for (const added of patch.added_nodes) {
    const fallbackPosition = added.position ?? { x: 550, y: 560 };
    const newNode: FlowNode = {
      id: added.id,
      type: "courseNode",
      position: fallbackPosition,
      data: {
        course_id: added.id,
        title: added.label,
        platform: "Remediation",
        difficulty: "intermediate",
        duration_hours: 0,
        skill_tags: [],
        score: 0,
        shap_values: {
          gap_severity: 0,
          tag_similarity: 0,
          course_rating: 0,
          difficulty_match: 0,
          prereq_satisfaction: 0,
        },
        explanation_text: "Remediation node added by Phase 4.",
        url: "",
        status: added.status,
        is_unlocked: true,
      },
    };
    nextNodes.push(newNode);
  }

  // ---- 4. Remove edges ----
  let nextEdges = edges.filter(
    (e) => !patch.removed_edge_ids.includes(e.id)
  );

  // ---- 5. Add new edges ----
  for (const ae of patch.added_edges as RoadmapEdge[]) {
    const flowEdge: FlowEdge = {
      id: ae.id,
      source: ae.source,
      target: ae.target,
      animated: ae.animated,
      label: ae.label,
      style:
        ae.type === "remediation"
          ? { stroke: "#f97316", strokeDasharray: "6 3" }
          : undefined,
    };
    nextEdges.push(flowEdge);
  }

  return { nodes: nextNodes, edges: nextEdges };
}
