"use client";
/**
 * components/CourseNode.tsx
 * roadmap.sh-inspired rectangular node with left accent bar.
 * Light theme, clean typography, status-driven colour system.
 */

import { memo } from "react";
import { Handle, Position, type NodeProps, type Node } from "@xyflow/react";
import { Lock, Clock, Zap } from "lucide-react";
import type { RoadmapNodeData } from "@/lib/types";

// ---- Status → visual treatment ----
const STATUS_MAP: Record<
  string,
  { accent: string; bg: string; text: string; badge: string; badgeText: string }
> = {
  pending: {
    accent: "bg-gray-300",
    bg: "bg-white",
    text: "text-gray-800",
    badge: "bg-gray-100 text-gray-500",
    badgeText: "Not started",
  },
  in_progress: {
    accent: "bg-blue-500",
    bg: "bg-blue-50",
    text: "text-blue-900",
    badge: "bg-blue-100 text-blue-700",
    badgeText: "In progress",
  },
  completed: {
    accent: "bg-emerald-500",
    bg: "bg-emerald-50",
    text: "text-emerald-900",
    badge: "bg-emerald-100 text-emerald-700",
    badgeText: "Done ✓",
  },
  failed: {
    accent: "bg-red-500",
    bg: "bg-red-50",
    text: "text-red-900",
    badge: "bg-red-100 text-red-700",
    badgeText: "Failed",
  },
  skipped: {
    accent: "bg-amber-400",
    bg: "bg-amber-50",
    text: "text-amber-900",
    badge: "bg-amber-100 text-amber-700",
    badgeText: "Skipped",
  },
};

// ---- Difficulty ----
const DIFF_MAP: Record<string, string> = {
  beginner: "bg-emerald-100 text-emerald-700",
  intermediate: "bg-blue-100 text-blue-700",
  advanced: "bg-purple-100 text-purple-700",
};

type CourseNodeProps = NodeProps<Node<RoadmapNodeData>>;

function CourseNode({ data, selected }: CourseNodeProps) {
  const s = STATUS_MAP[data.status] ?? STATUS_MAP.pending;
  const diff = DIFF_MAP[data.difficulty] ?? DIFF_MAP.intermediate;
  const fitPct = Math.round(data.score * 100);

  return (
    <div
      className={`
        relative flex w-60 rounded-lg border overflow-hidden
        shadow-sm transition-all duration-150 select-none
        ${s.bg}
        ${selected
          ? "border-blue-500 shadow-md ring-2 ring-blue-200"
          : "border-gray-200 hover:border-blue-400 hover:shadow-md"}
        ${!data.is_unlocked ? "opacity-60" : "cursor-pointer"}
      `}
      role="button"
      aria-label={`${data.title} — ${s.badgeText}`}
      tabIndex={data.is_unlocked ? 0 : -1}
    >
      {/* Left accent bar */}
      <div className={`w-1.5 shrink-0 ${s.accent}`} />

      {/* Content */}
      <div className="flex-1 px-3 py-2.5 min-w-0">
        <Handle
          type="target"
          position={Position.Top}
          className="!border-gray-300 !bg-white !w-2.5 !h-2.5"
        />

        {/* Title row */}
        <div className="flex items-start justify-between gap-1 mb-1.5">
          <p className={`text-[13px] font-semibold leading-snug line-clamp-2 ${s.text}`}>
            {data.title}
          </p>
          {!data.is_unlocked && (
            <Lock className="h-3.5 w-3.5 shrink-0 text-gray-400 mt-0.5" aria-hidden />
          )}
        </div>

        {/* Tags row */}
        <div className="flex items-center flex-wrap gap-1 mb-2">
          <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${diff}`}>
            {data.difficulty}
          </span>
          <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-500">
            {data.platform}
          </span>
          <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${s.badge}`}>
            {s.badgeText}
          </span>
        </div>

        {/* Meta row */}
        <div className="flex items-center gap-3 text-[11px] text-gray-500">
          <span className="flex items-center gap-0.5">
            <Clock className="h-3 w-3" aria-hidden />
            {data.duration_hours}h
          </span>
          <span className="flex items-center gap-0.5">
            <Zap className="h-3 w-3 text-amber-500" aria-hidden />
            {fitPct}% fit
          </span>
        </div>

        {/* Fit bar */}
        <div className="mt-2 h-1 rounded-full bg-gray-200 overflow-hidden">
          <div
            className="h-full rounded-full bg-blue-500 transition-all duration-500"
            style={{ width: `${fitPct}%` }}
            role="progressbar"
            aria-valuenow={fitPct}
            aria-valuemin={0}
            aria-valuemax={100}
          />
        </div>

        <Handle
          type="source"
          position={Position.Bottom}
          className="!border-gray-300 !bg-white !w-2.5 !h-2.5"
        />
      </div>
    </div>
  );
}

export default memo(CourseNode);
