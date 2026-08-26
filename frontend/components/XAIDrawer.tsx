"use client";
/**
 * components/XAIDrawer.tsx
 * roadmap.sh-style right-side detail panel.
 * Light theme, SHAP bar chart, skill tags, CTA.
 */

import { X, ExternalLink, Clock, TrendingUp, Tag, BrainCircuit } from "lucide-react";
import type { RoadmapNodeData, ShapValues } from "@/lib/types";

const FEATURE_LABELS: Record<keyof ShapValues, string> = {
  gap_severity:       "Skill Gap Severity",
  tag_similarity:     "Role Tag Match",
  course_rating:      "Course Rating",
  difficulty_match:   "Difficulty Fit",
  prereq_satisfaction:"Prerequisites Met",
};

const FEATURE_BAR: Record<keyof ShapValues, string> = {
  gap_severity:       "bg-red-400",
  tag_similarity:     "bg-blue-500",
  course_rating:      "bg-emerald-500",
  difficulty_match:   "bg-violet-500",
  prereq_satisfaction:"bg-amber-400",
};

const STATUS_CHIP: Record<string, string> = {
  pending:     "bg-gray-100 text-gray-600",
  in_progress: "bg-blue-100 text-blue-700",
  completed:   "bg-emerald-100 text-emerald-700",
  failed:      "bg-red-100 text-red-700",
  skipped:     "bg-amber-100 text-amber-700",
};
const STATUS_LABEL: Record<string, string> = {
  pending:     "Not started",
  in_progress: "In progress",
  completed:   "Completed ✓",
  failed:      "Failed — retry",
  skipped:     "Skipped",
};

interface Props {
  node: RoadmapNodeData | null;
  onClose: () => void;
}

export default function XAIDrawer({ node, onClose }: Props) {
  if (!node) return null;

  const shapEntries = (
    Object.entries(node.shap_values) as [keyof ShapValues, number][]
  ).sort(([, a], [, b]) => b - a);
  const maxShap = Math.max(...shapEntries.map(([, v]) => Math.abs(v)), 0.001);

  return (
    <>
      {/* Scrim */}
      <div
        className="fixed inset-0 z-40 bg-black/20"
        onClick={onClose}
        aria-hidden
      />

      {/* Panel */}
      <aside
        role="dialog"
        aria-modal="true"
        aria-label={`Details: ${node.title}`}
        className="fixed right-0 top-0 z-50 h-full w-[360px] bg-white border-l border-gray-200 shadow-xl flex flex-col"
      >
        {/* ── Header ── */}
        <div className="flex items-start gap-3 px-5 py-4 border-b border-gray-100">
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-blue-600 uppercase tracking-wide mb-0.5">
              {node.platform}
            </p>
            <h2 className="text-base font-bold text-gray-900 leading-snug">
              {node.title}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="shrink-0 mt-0.5 p-1 rounded-md text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors"
            aria-label="Close panel"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* ── Body ── */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">

          {/* Stat chips */}
          <div className="grid grid-cols-3 gap-2">
            <StatChip icon={<Clock className="h-3.5 w-3.5 text-gray-400" />} label="Duration" value={`${node.duration_hours}h`} />
            <StatChip icon={<TrendingUp className="h-3.5 w-3.5 text-blue-500" />} label="AI Fit" value={`${Math.round(node.score * 100)}%`} />
            <StatChip icon={<Tag className="h-3.5 w-3.5 text-violet-500" />} label="Level" value={node.difficulty} />
          </div>

          {/* Status */}
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-gray-400 mb-1.5">Status</p>
            <span className={`inline-block text-xs font-medium px-2.5 py-1 rounded-full ${STATUS_CHIP[node.status] ?? STATUS_CHIP.pending}`}>
              {STATUS_LABEL[node.status] ?? "Unknown"}
            </span>
          </div>

          {/* Why recommended */}
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-gray-400 mb-1.5">Why recommended</p>
            <p className="text-sm text-gray-700 leading-relaxed bg-blue-50 border border-blue-100 rounded-lg p-3">
              {node.explanation_text}
            </p>
          </div>

          {/* SHAP bars */}
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <BrainCircuit className="h-3.5 w-3.5 text-violet-500" aria-hidden />
              <p className="text-[11px] font-semibold uppercase tracking-widest text-gray-400">
                ML feature importance
              </p>
            </div>
            <div className="space-y-2.5">
              {shapEntries.map(([key, value]) => (
                <div key={key}>
                  <div className="flex justify-between text-xs text-gray-500 mb-1">
                    <span>{FEATURE_LABELS[key]}</span>
                    <span className="font-medium text-gray-700">{value.toFixed(3)}</span>
                  </div>
                  <div className="h-2 rounded-full bg-gray-100 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${FEATURE_BAR[key]}`}
                      style={{ width: `${(Math.abs(value) / maxShap) * 100}%` }}
                      role="progressbar"
                      aria-valuenow={value}
                      aria-valuemin={0}
                      aria-valuemax={maxShap}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Skill tags */}
          {node.skill_tags.length > 0 && (
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-widest text-gray-400 mb-2">Skills covered</p>
              <div className="flex flex-wrap gap-1.5">
                {node.skill_tags.map((tag) => (
                  <span
                    key={tag}
                    className="text-[11px] px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 border border-gray-200"
                  >
                    {tag.replace(/_/g, " ")}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* ── Footer CTA ── */}
        {node.url && (
          <div className="px-5 py-4 border-t border-gray-100 bg-gray-50">
            <a
              href={node.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-2 w-full py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold transition-colors shadow-sm"
            >
              <ExternalLink className="h-4 w-4" />
              Start on {node.platform}
            </a>
          </div>
        )}
      </aside>
    </>
  );
}

function StatChip({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="flex flex-col items-center gap-1 bg-gray-50 border border-gray-200 rounded-lg py-2 px-1 text-center">
      {icon}
      <span className="text-[10px] text-gray-400 uppercase tracking-wide">{label}</span>
      <span className="text-xs font-semibold text-gray-700 capitalize">{value}</span>
    </div>
  );
}
