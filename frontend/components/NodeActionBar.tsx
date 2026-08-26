"use client";
/**
 * components/NodeActionBar.tsx
 * Floating action bar that appears when a node is selected.
 * Sends RecalibrateRequest signals to the backend (Phase 4).
 */

import { CheckCircle, XCircle, SkipForward, Loader2 } from "lucide-react";
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
      const patch = await recalibrateRoadmap(req);
      onPatch(patch);
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
      className="flex items-center gap-2 bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 shadow-xl"
    >
      <span className="text-xs text-slate-400 mr-1 max-w-[140px] truncate">
        {node.title}
      </span>

      <ActionButton
        label="Mark complete"
        icon={<CheckCircle className="h-4 w-4" />}
        colour="text-emerald-400 hover:bg-emerald-900/40"
        loading={loading === "quiz_pass"}
        disabled={!node.is_unlocked || node.status === "completed"}
        onClick={() => send({ ...base, trigger: "quiz_pass", quiz_score: 1.0 })}
      />

      <ActionButton
        label="Fail quiz"
        icon={<XCircle className="h-4 w-4" />}
        colour="text-red-400 hover:bg-red-900/40"
        loading={loading === "quiz_failure"}
        disabled={!node.is_unlocked}
        onClick={() =>
          send({ ...base, trigger: "quiz_failure", quiz_score: 0.3 })
        }
      />

      <ActionButton
        label="Skip node"
        icon={<SkipForward className="h-4 w-4" />}
        colour="text-yellow-400 hover:bg-yellow-900/40"
        loading={loading === "module_skip"}
        disabled={node.status === "completed" || node.status === "skipped"}
        onClick={() => send({ ...base, trigger: "module_skip" })}
      />
    </div>
  );
}

function ActionButton({
  label,
  icon,
  colour,
  loading,
  disabled,
  onClick,
}: {
  label: string;
  icon: React.ReactNode;
  colour: string;
  loading: boolean;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <button
      aria-label={label}
      title={label}
      disabled={disabled || loading}
      onClick={onClick}
      className={`p-1.5 rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${colour}`}
    >
      {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : icon}
    </button>
  );
}
