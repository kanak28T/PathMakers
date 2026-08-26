"use client";
/**
 * components/RoadmapCanvas.tsx
 * Light-theme React Flow canvas, roadmap.sh inspired.
 * Must be imported with { ssr: false } in page.tsx.
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

type CourseFlowNode = Node<RoadmapNodeData>;
const NODE_TYPES = { courseNode: CourseNode };

function toFlowEdge(e: {
  id: string; source: string; target: string;
  type?: string; animated?: boolean; label?: string;
}): Edge {
  const base: Edge = {
    id: e.id, source: e.source, target: e.target,
    animated: e.animated ?? false, label: e.label ?? "",
  };
  if (e.type === "remediation") return {
    ...base,
    style: { stroke: "#f97316", strokeWidth: 2, strokeDasharray: "6 3" },
    labelStyle: { fill: "#f97316", fontSize: 10 },
  };
  if (e.type === "recommended") return {
    ...base,
    style: { stroke: "#6366f1", strokeWidth: 1.5, strokeDasharray: "4 2" },
    labelStyle: { fill: "#6366f1", fontSize: 10 },
  };
  return {
    ...base,
    style: { stroke: "#94a3b8", strokeWidth: 1.5 },
    labelStyle: { fill: "#64748b", fontSize: 10 },
  };
}

interface Props {
  intake?: LearnerIntakeForm & { learner_id: string };
}

export default function RoadmapCanvas({ intake }: Props) {
  const [nodes, setNodes, onNodesChange] = useNodesState<CourseFlowNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [graphMeta, setGraphMeta] = useState<Pick<
    RoadmapGraphResponse, "learner_id" | "target_role" | "total_hours"
  > | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [toastMsg, setToastMsg] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const data: RoadmapGraphResponse = intake
          ? await generateRoadmap(intake)
          : await fetchMockRoadmap();

        setNodes(data.nodes.map((n) => ({
          id: n.id, type: n.type, position: n.position, data: n.data,
        })));
        setEdges(data.edges.map(toFlowEdge));
        setGraphMeta({
          learner_id: data.learner_id,
          target_role: data.target_role,
          total_hours: data.total_hours,
        });
      } catch {
        setLoadError("Could not load roadmap. Is the backend running at localhost:8000?");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [intake, setNodes, setEdges]);

  const handlePatch = useCallback((patch: RoadmapPatchEvent) => {
    setNodes((cur) => applyPatch(cur, [], patch).nodes);
    setEdges((cur) => applyPatch([], cur, patch).edges);
    setToastMsg(patch.summary);
  }, [setNodes, setEdges]);

  useGraphPatch(graphMeta?.learner_id ?? null, handlePatch);

  const onNodeClick: NodeMouseHandler<CourseFlowNode> = useCallback(
    (_e, node) => setSelectedNodeId(node.id), []
  );

  const liveSelectedNode = useMemo(() => {
    if (!selectedNodeId) return null;
    return (nodes.find((n) => n.id === selectedNodeId) as CourseFlowNode | undefined)?.data ?? null;
  }, [nodes, selectedNodeId]);

  // ---- stats for top panel ----
  const stats = useMemo(() => {
    const total = nodes.length;
    const done = nodes.filter((n) => (n as CourseFlowNode).data.status === "completed").length;
    return { total, done, pct: total ? Math.round((done / total) * 100) : 0 };
  }, [nodes]);

  if (loadError) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center space-y-2">
          <p className="text-gray-500 text-sm">{loadError}</p>
          <p className="text-gray-400 text-xs">The canvas still shows the demo roadmap below.</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center gap-2 text-gray-400 text-sm">
        <span className="inline-block h-4 w-4 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
        Building your roadmap…
      </div>
    );
  }

  return (
    <div className="relative h-full w-full bg-gray-50">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        onPaneClick={() => setSelectedNodeId(null)}
        nodeTypes={NODE_TYPES}
        fitView
        fitViewOptions={{ padding: 0.35 }}
        minZoom={0.2}
        maxZoom={1.8}
        colorMode="light"
        defaultEdgeOptions={{ type: "smoothstep" }}
        aria-label="Learning roadmap flowchart"
      >
        <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="#e2e8f0" />
        <Controls showInteractive={false} aria-label="Canvas controls" />
        <MiniMap
          nodeColor={(n) => ({
            completed:   "#10b981",
            in_progress: "#3b82f6",
            failed:      "#ef4444",
            skipped:     "#f59e0b",
            pending:     "#cbd5e1",
          }[(n as CourseFlowNode).data?.status ?? "pending"] ?? "#cbd5e1")}
          maskColor="rgb(249 250 251 / 0.7)"
        />

        {/* ── Top-left: roadmap header ── */}
        {graphMeta && (
          <Panel position="top-left">
            <div className="bg-white border border-gray-200 rounded-xl px-4 py-3 shadow-sm min-w-[200px]">
              <p className="text-xs text-blue-600 font-semibold uppercase tracking-wide mb-0.5">
                Your Roadmap
              </p>
              <p className="text-sm font-bold text-gray-900 capitalize">
                {graphMeta.target_role.replace(/_/g, " ")}
              </p>
              <p className="text-xs text-gray-500 mt-0.5">
                {graphMeta.total_hours}h · {stats.total} courses
              </p>
              {/* Progress bar */}
              <div className="mt-2 h-1.5 rounded-full bg-gray-100 overflow-hidden">
                <div
                  className="h-full rounded-full bg-blue-500 transition-all duration-700"
                  style={{ width: `${stats.pct}%` }}
                />
              </div>
              <p className="text-[10px] text-gray-400 mt-0.5">
                {stats.done}/{stats.total} completed
              </p>
            </div>
          </Panel>
        )}

        {/* ── Top-right: legend ── */}
        <Panel position="top-right">
          <div className="bg-white border border-gray-200 rounded-xl px-3 py-2.5 shadow-sm text-[11px] text-gray-600 space-y-1.5">
            <p className="font-semibold text-gray-700 mb-1">Legend</p>
            {[
              { cls: "bg-gray-300",   label: "Not started" },
              { cls: "bg-blue-500",   label: "In progress", pulse: true },
              { cls: "bg-emerald-500",label: "Completed" },
              { cls: "bg-red-500",    label: "Failed" },
              { cls: "bg-amber-400",  label: "Skipped" },
            ].map(({ cls, label, pulse }) => (
              <div key={label} className="flex items-center gap-2">
                <span className={`w-2.5 h-2.5 rounded-sm shrink-0 ${cls} ${pulse ? "pulse" : ""}`} />
                {label}
              </div>
            ))}
            <hr className="border-gray-100 my-1" />
            <div className="flex items-center gap-2">
              <span className="w-5 border-t-2 border-gray-400" />
              Prerequisite
            </div>
            <div className="flex items-center gap-2">
              <span className="w-5 border-t-2 border-dashed border-violet-400" />
              Recommended
            </div>
            <div className="flex items-center gap-2">
              <span className="w-5 border-t-2 border-dashed border-orange-400" />
              Remediation
            </div>
          </div>
        </Panel>

        {/* ── Bottom-center: node action bar ── */}
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

      <XAIDrawer node={liveSelectedNode} onClose={() => setSelectedNodeId(null)} />
      <PatchToast message={toastMsg} onDismiss={() => setToastMsg(null)} />
    </div>
  );
}
