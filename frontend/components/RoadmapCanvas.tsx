"use client";
/**
 * components/RoadmapCanvas.tsx
 * Core interactive canvas.  Must be imported with { ssr: false } in page.tsx.
 *
 * Responsibilities:
 *  - Fetches /api/roadmap/mock on mount (swapped for /api/roadmap/generate post-Day4)
 *  - Renders nodes via custom CourseNode component
 *  - Listens for Phase 4 SSE patches via useGraphPatch and merges diffs
 *  - Opens XAIDrawer on node click
 *  - Exposes NodeActionBar for mark-complete / fail-quiz / skip actions
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
  Panel,
  type Node,
  type Edge,
  type NodeMouseHandler,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import CourseNode from "./CourseNode";
import XAIDrawer from "./XAIDrawer";
import NodeActionBar from "./NodeActionBar";
import PatchToast from "./PatchToast";

import { fetchMockRoadmap, generateRoadmap } from "@/lib/api";
import { applyPatch } from "@/lib/patchGraph";
import { useGraphPatch } from "@/hooks/useGraphPatch";
import type {
  RoadmapNodeData,
  RoadmapGraphResponse,
  RoadmapPatchEvent,
  LearnerIntakeForm,
} from "@/lib/types";

// @xyflow/react requires node data to extend Record<string, unknown>
// RoadmapNodeData already does via its interface definition in lib/types.ts
type CourseFlowNode = Node<RoadmapNodeData>;

const NODE_TYPES = { courseNode: CourseNode };

function toFlowEdge(e: {
  id: string;
  source: string;
  target: string;
  type?: string;
  animated?: boolean;
  label?: string;
}): Edge {
  const base: Edge = {
    id: e.id,
    source: e.source,
    target: e.target,
    animated: e.animated ?? false,
    label: e.label ?? "",
  };
  if (e.type === "remediation") {
    return { ...base, style: { stroke: "#f97316", strokeDasharray: "6 3" } };
  }
  if (e.type === "recommended") {
    return { ...base, style: { stroke: "#6366f1", strokeDasharray: "4 2" } };
  }
  return { ...base, style: { stroke: "#475569" } };
}

interface Props {
  intake?: LearnerIntakeForm & { learner_id: string };
}

export default function RoadmapCanvas({ intake }: Props) {
  const [nodes, setNodes, onNodesChange] = useNodesState<CourseFlowNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const [graphMeta, setGraphMeta] = useState<Pick<
    RoadmapGraphResponse,
    "learner_id" | "target_role" | "total_hours"
  > | null>(null);

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [toastMsg, setToastMsg] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  // ---- Load graph ----
  useEffect(() => {
    async function load() {
      try {
        const data: RoadmapGraphResponse = intake
          ? await generateRoadmap(intake)
          : await fetchMockRoadmap();

        const flowNodes: CourseFlowNode[] = data.nodes.map((n) => ({
          id: n.id,
          type: n.type,
          position: n.position,
          data: n.data,
        }));

        const flowEdges: Edge[] = data.edges.map(toFlowEdge);

        setNodes(flowNodes);
        setEdges(flowEdges);
        setGraphMeta({
          learner_id: data.learner_id,
          target_role: data.target_role,
          total_hours: data.total_hours,
        });
      } catch (err) {
        setLoadError("Could not load roadmap. Is the backend running?");
        console.error(err);
      }
    }
    load();
  }, [intake, setNodes, setEdges]);

  // ---- SSE / action patch handler ----
  const handlePatch = useCallback(
    (patch: RoadmapPatchEvent) => {
      setNodes((cur) => {
        const { nodes: nextNodes } = applyPatch(cur, edges, patch);
        return nextNodes;
      });
      setEdges((cur) => {
        const { edges: nextEdges } = applyPatch(nodes, cur, patch);
        return nextEdges;
      });
      setToastMsg(patch.summary);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [setNodes, setEdges]
  );

  useGraphPatch(graphMeta?.learner_id ?? null, handlePatch);

  // ---- Node click → open XAI drawer ----
  const onNodeClick: NodeMouseHandler<CourseFlowNode> = useCallback(
    (_event, node) => {
      setSelectedNodeId(node.id);
    },
    []
  );

  // ---- Live selected node data (re-reads from nodes state on every patch) ----
  const liveSelectedNode: RoadmapNodeData | null = useMemo(() => {
    if (!selectedNodeId) return null;
    const found = nodes.find((n) => n.id === selectedNodeId);
    return found ? found.data : null;
  }, [nodes, selectedNodeId]);

  if (loadError) {
    return (
      <div className="flex h-full items-center justify-center text-slate-400 text-sm">
        {loadError}
      </div>
    );
  }

  return (
    <div className="relative h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        nodeTypes={NODE_TYPES}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        minZoom={0.3}
        maxZoom={1.5}
        colorMode="dark"
        aria-label="Learning roadmap graph"
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1}
          color="#1e293b"
        />
        <Controls aria-label="Canvas controls" />
        <MiniMap
          nodeColor={(n) => {
            const d = (n as CourseFlowNode).data;
            const status = d?.status as string | undefined;
            return (
              ({
                completed: "#10b981",
                in_progress: "#3b82f6",
                failed: "#ef4444",
                skipped: "#f59e0b",
                pending: "#475569",
              } as Record<string, string>)[status ?? "pending"] ?? "#475569"
            );
          }}
        />

        {/* Meta panel top-left */}
        {graphMeta && (
          <Panel
            position="top-left"
            className="bg-slate-900/90 border border-slate-700 rounded-xl px-4 py-2.5 text-sm"
          >
            <p className="text-white font-semibold capitalize">
              {graphMeta.target_role.replace(/_/g, " ")}
            </p>
            <p className="text-slate-400 text-xs">
              {graphMeta.total_hours}h total · {nodes.length} courses
            </p>
          </Panel>
        )}

        {/* Action bar for selected node */}
        {liveSelectedNode && graphMeta && (
          <Panel position="bottom-center">
            <NodeActionBar
              node={liveSelectedNode}
              learnerId={graphMeta.learner_id}
              onPatch={handlePatch}
            />
          </Panel>
        )}
      </ReactFlow>

      {/* XAI drawer */}
      <XAIDrawer
        node={liveSelectedNode}
        onClose={() => setSelectedNodeId(null)}
      />

      {/* Patch toast */}
      <PatchToast message={toastMsg} onDismiss={() => setToastMsg(null)} />
    </div>
  );
}
