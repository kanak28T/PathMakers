"use client";
/**
 * components/NodeActionBar.tsx
 * Light-theme floating action bar for selected nodes.
 */

import { CheckCircle, XCircle, SkipForward, Loader2, Info } from "lucide-react";
import type { RoadmapNodeData, RecalibrateRequest } from "@/lib/types";
import { recalibrateRoadmap } from "@/lib/api";
import { useState } from "react";

interface Props {
  node: RoadmapNodeData;
  learnerId: string;
  onPatch: (patch: Awaited<ReturnType<typeof recalibrateRoadmap>>) => void;
}

export default function NodeActionBar({ node, learnerId, onPatch }: Props) {
  const [loading, setLoading] = useState<string | null>(null);

  async function send(req: RecalibrateRequest) {
    setLoading(req.trigger);
    try {
      onPatch(await recalibrateRoadmap(req));
    } finally {
      setLoading(null);
    }
  }

  const base: Omit<RecalibrateRequest, "trigger"> = {
    learner_id: learnerId,
    node_id: node.course_id,
  };

  return (
    <div
      role="toolbar"
      aria-label={`Actions for ${node.title}`}
      className="flex items-center gap-1 bg-white border border-gray-200 rounded-xl px-3 py-2 shadow-lg"
    >
      {/* Node label */}
      <div className="flex items-center gap-1.5 mr-2 pr-2 border-r border-gray-100">
        <Info className="h-3.5 w-3.5 text-gray-400" aria-hidden />
        <span className="text-xs font-medium text-gray-700 max-w-[160px] truncate">
          {node.title}
        </span>
      </div>

      <ActionBtn
        label="Mark complete"
        icon={<CheckCircle className="h-4 w-4" />}
        cls="text-emerald-600 hover:bg-emerald-50"
        loading={loading === "quiz_pass"}
        disabled={!node.is_unlocked || node.status === "completed"}
        onClick={() => send({ ...base, trigger: "quiz_pass", quiz_score: 1.0 })}
      />
      <ActionBtn
        label="Fail quiz"
        icon={<XCircle className="h-4 w-4" />}
        cls="text-red-500 hover:bg-red-50"
        loading={loading === "quiz_failure"}
        disabled={!node.is_unlocked}
        onClick={() => send({ ...base, trigger: "quiz_failure", quiz_score: 0.3 })}
      />
      <ActionBtn
        label="Skip node"
        icon={<SkipForward className="h-4 w-4" />}
        cls="text-amber-500 hover:bg-amber-50"
        loading={loading === "module_skip"}
        disabled={node.status === "completed" || node.status === "skipped"}
        onClick={() => send({ ...base, trigger: "module_skip" })}
      />
    </div>
  );
}

function ActionBtn({
  label, icon, cls, loading, disabled, onClick,
}: {
  label: string; icon: React.ReactNode; cls: string;
  loading: boolean; disabled: boolean; onClick: () => void;
}) {
  return (
    <button
      aria-label={label}
      title={label}
      disabled={disabled || loading}
      onClick={onClick}
      className={`p-1.5 rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${cls}`}
    >
      {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : icon}
    </button>
  );
}
