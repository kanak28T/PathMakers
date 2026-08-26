"use client";
/**
 * components/XAIDrawer.tsx
 * Slide-in panel shown when a user clicks a roadmap node.
 * Displays course details + visual SHAP feature-importance bars.
 */

import { X, ExternalLink, Tag, Clock, TrendingUp } from "lucide-react";
import type { RoadmapNodeData, ShapValues } from "@/lib/types";

const FEATURE_LABELS: Record<keyof ShapValues, string> = {
  gap_severity: "Skill Gap Severity",
  tag_similarity: "Role Tag Match",
  course_rating: "Course Rating",
  difficulty_match: "Difficulty Fit",
  prereq_satisfaction: "Prerequisites Met",
};

const FEATURE_COLORS: Record<keyof ShapValues, string> = {
  gap_severity: "bg-red-500",
  tag_similarity: "bg-indigo-500",
  course_rating: "bg-emerald-500",
  difficulty_match: "bg-blue-500",
  prereq_satisfaction: "bg-purple-500",
};

interface Props {
  node: RoadmapNodeData | null;
  onClose: () => void;
}

export default function XAIDrawer({ node, onClose }: Props) {
  if (!node) return null;

  const shapEntries = Object.entries(node.shap_values) as [
    keyof ShapValues,
    number
  ][];
  const maxShap = Math.max(...shapEntries.map(([, v]) => Math.abs(v)));

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden
      />

      {/* Drawer panel */}
      <aside
        role="dialog"
        aria-modal="true"
        aria-label={`Course details: ${node.title}`}
        className="fixed right-0 top-0 z-50 h-full w-80 overflow-y-auto bg-slate-900 border-l border-slate-700 shadow-2xl flex flex-col"
      >
        {/* Header */}
        <div className="flex items-start justify-between p-4 border-b border-slate-700">
          <div className="flex-1 pr-2">
            <h2 className="text-base font-bold text-white leading-snug">
              {node.title}
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">{node.platform}</p>
          </div>
          <button
            onClick={onClose}
            className="shrink-0 text-slate-400 hover:text-white transition-colors"
            aria-label="Close drawer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex-1 p-4 space-y-5">
          {/* Meta */}
          <div className="grid grid-cols-2 gap-2 text-sm">
            <MetaChip icon={<Clock className="h-3.5 w-3.5" />} label={`${node.duration_hours}h`} />
            <MetaChip
              icon={<TrendingUp className="h-3.5 w-3.5" />}
              label={`${(node.score * 100).toFixed(0)}% fit`}
            />
            <span className="col-span-2">
              <MetaChip
                icon={<Tag className="h-3.5 w-3.5" />}
                label={node.difficulty}
                wide
              />
            </span>
          </div>

          {/* Status */}
          <StatusBadge status={node.status} />

          {/* AI Explanation */}
          <section aria-label="AI explanation">
            <h3 className="text-xs uppercase tracking-widest text-slate-500 mb-1">
              Why recommended
            </h3>
            <p className="text-sm text-slate-300 leading-relaxed">
              {node.explanation_text}
            </p>
          </section>

          {/* SHAP Feature Importance */}
          <section aria-label="Feature importance">
            <h3 className="text-xs uppercase tracking-widest text-slate-500 mb-2">
              ML feature importance
            </h3>
            <div className="space-y-2">
              {shapEntries
                .sort(([, a], [, b]) => b - a)
                .map(([key, value]) => (
                  <div key={key}>
                    <div className="flex justify-between text-xs text-slate-400 mb-0.5">
                      <span>{FEATURE_LABELS[key]}</span>
                      <span>{value.toFixed(3)}</span>
                    </div>
                    <div className="h-2 rounded-full bg-slate-700 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${FEATURE_COLORS[key]}`}
                        style={{
                          width: `${(Math.abs(value) / maxShap) * 100}%`,
                        }}
                        role="progressbar"
                        aria-valuenow={value}
                        aria-valuemin={0}
                        aria-valuemax={maxShap}
                      />
                    </div>
                  </div>
                ))}
            </div>
          </section>

          {/* Skill tags */}
          {node.skill_tags.length > 0 && (
            <section aria-label="Skill tags">
              <h3 className="text-xs uppercase tracking-widest text-slate-500 mb-2">
                Skills covered
              </h3>
              <div className="flex flex-wrap gap-1">
                {node.skill_tags.map((tag) => (
                  <span
                    key={tag}
                    className="text-[11px] px-2 py-0.5 rounded-full bg-slate-700 text-slate-300"
                  >
                    {tag.replace(/_/g, " ")}
                  </span>
                ))}
              </div>
            </section>
          )}
        </div>

        {/* Footer CTA */}
        {node.url && (
          <div className="p-4 border-t border-slate-700">
            <a
              href={node.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-2 w-full py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors"
            >
              <ExternalLink className="h-4 w-4" />
              Open on {node.platform}
            </a>
          </div>
        )}
      </aside>
    </>
  );
}

// ---------------------------------------------------------------------------
// Small sub-components
// ---------------------------------------------------------------------------

function MetaChip({
  icon,
  label,
  wide,
}: {
  icon: React.ReactNode;
  label: string;
  wide?: boolean;
}) {
  return (
    <div
      className={`flex items-center gap-1.5 text-xs text-slate-300 bg-slate-800 px-2 py-1 rounded-md ${wide ? "w-full" : ""}`}
    >
      <span className="text-slate-500">{icon}</span>
      {label}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    pending: { label: "Not started", cls: "bg-slate-700 text-slate-300" },
    in_progress: { label: "In progress", cls: "bg-blue-700 text-blue-200" },
    completed: { label: "Completed ✓", cls: "bg-emerald-700 text-emerald-200" },
    failed: { label: "Failed — retry", cls: "bg-red-700 text-red-200" },
    skipped: { label: "Skipped", cls: "bg-yellow-700 text-yellow-200" },
  };
  const s = map[status] ?? map.pending;
  return (
    <span
      className={`inline-block text-xs px-2 py-0.5 rounded-full font-medium ${s.cls}`}
    >
      {s.label}
    </span>
  );
}
