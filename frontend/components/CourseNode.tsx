"use client";
/**
 * components/CourseNode.tsx
 * Custom React Flow node for a single course in the learning roadmap.
 * Status drives border colour; locked nodes show a padlock overlay.
 */

import { memo } from "react";
import { Handle, Position, type NodeProps, type Node } from "@xyflow/react";
import { Lock, ExternalLink, Clock, BarChart2 } from "lucide-react";
import type { RoadmapNodeData } from "@/lib/types";

const STATUS_STYLES: Record<string, string> = {
  pending: "border-slate-600 bg-slate-800",
  in_progress: "border-blue-500 bg-blue-950 ring-2 ring-blue-500/40",
  completed: "border-emerald-500 bg-emerald-950",
  failed: "border-red-500 bg-red-950",
  skipped: "border-yellow-500 bg-yellow-950 opacity-60",
};

const DIFFICULTY_BADGE: Record<string, string> = {
  beginner: "bg-emerald-700/60 text-emerald-200",
  intermediate: "bg-blue-700/60 text-blue-200",
  advanced: "bg-purple-700/60 text-purple-200",
};

type CourseNodeProps = NodeProps<Node<RoadmapNodeData>>;

function CourseNode({ data, selected }: CourseNodeProps) {
  const statusClass = STATUS_STYLES[data.status] ?? STATUS_STYLES.pending;
  const diffClass =
    DIFFICULTY_BADGE[data.difficulty] ?? DIFFICULTY_BADGE.intermediate;

  return (
    <div
      className={`
        relative w-56 rounded-xl border-2 p-3 shadow-lg transition-all duration-200
        ${statusClass}
        ${selected ? "ring-2 ring-indigo-400 ring-offset-1 ring-offset-slate-900" : ""}
        ${!data.is_unlocked ? "opacity-50" : "hover:scale-[1.02] cursor-pointer"}
      `}
      role="button"
      aria-label={`Course: ${data.title}, status: ${data.status}`}
      tabIndex={data.is_unlocked ? 0 : -1}
    >
      {/* Locked overlay */}
      {!data.is_unlocked && (
        <div className="absolute inset-0 flex items-center justify-center rounded-xl bg-slate-900/60 z-10">
          <Lock className="h-6 w-6 text-slate-400" aria-hidden />
        </div>
      )}

      {/* Top handles */}
      <Handle type="target" position={Position.Top} className="!bg-slate-500" />

      {/* Header */}
      <div className="flex items-start justify-between gap-1 mb-2">
        <p className="text-sm font-semibold text-white leading-tight line-clamp-2">
          {data.title}
        </p>
        {data.url && (
          <a
            href={data.url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="shrink-0 text-slate-400 hover:text-indigo-400 transition-colors"
            aria-label={`Open ${data.title} on ${data.platform}`}
          >
            <ExternalLink className="h-4 w-4" />
          </a>
        )}
      </div>

      {/* Badges row */}
      <div className="flex items-center gap-1 flex-wrap mb-2">
        <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${diffClass}`}>
          {data.difficulty}
        </span>
        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-700 text-slate-300">
          {data.platform}
        </span>
      </div>

      {/* Meta row */}
      <div className="flex items-center gap-3 text-xs text-slate-400">
        <span className="flex items-center gap-1">
          <Clock className="h-3 w-3" aria-hidden />
          {data.duration_hours}h
        </span>
        <span className="flex items-center gap-1">
          <BarChart2 className="h-3 w-3" aria-hidden />
          {(data.score * 100).toFixed(0)}% fit
        </span>
      </div>

      {/* Status dot */}
      <div className="absolute top-2 right-2">
        <StatusDot status={data.status} />
      </div>

      {/* Bottom handle */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-slate-500"
      />
    </div>
  );
}

function StatusDot({ status }: { status: string }) {
  const colours: Record<string, string> = {
    pending: "bg-slate-500",
    in_progress: "bg-blue-400 animate-pulse",
    completed: "bg-emerald-400",
    failed: "bg-red-400",
    skipped: "bg-yellow-400",
  };
  return (
    <span
      className={`block h-2 w-2 rounded-full ${colours[status] ?? colours.pending}`}
      aria-hidden
    />
  );
}

export default memo(CourseNode);
