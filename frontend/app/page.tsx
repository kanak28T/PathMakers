/**
 * app/page.tsx
 * Root page — orchestrates intake flow → roadmap canvas.
 *
 * RoadmapCanvas uses React Flow which requires browser APIs.
 * It MUST be imported dynamically with { ssr: false } to prevent
 * hydration errors.  This is the Hydration Guard from the Day-1 spec.
 */

"use client";

import dynamic from "next/dynamic";
import { useState, useCallback } from "react";
import { Map, GitBranch } from "lucide-react";
import IntakeDrawer from "@/components/IntakeDrawer";
import type { LearnerIntakeForm } from "@/lib/types";
import { generateRoadmap } from "@/lib/api";

// ---- Hydration Guard: no SSR for the canvas ----
const RoadmapCanvas = dynamic(
  () => import("@/components/RoadmapCanvas"),
  { ssr: false }
);

type Phase = "intake" | "canvas";

export default function HomePage() {
  const [phase, setPhase] = useState<Phase>("intake");
  const [loading, setLoading] = useState(false);
  const [intake, setIntake] = useState<
    (LearnerIntakeForm & { learner_id: string }) | undefined
  >(undefined);

  const handleIntakeSubmit = useCallback(async (form: LearnerIntakeForm) => {
    setLoading(true);
    // Assign a client-side learner_id (backend will persist it in SQLite)
    const learnerId = `learner_${Date.now()}`;
    const full = { ...form, learner_id: learnerId };
    // Pre-warm the request so the canvas loads instantly
    try {
      await generateRoadmap(full);
    } catch {
      // generateRoadmap already falls back to mock internally — safe to ignore
    }
    setIntake(full);
    setLoading(false);
    setPhase("canvas");
  }, []);

  return (
    <main className="flex flex-col h-screen">
      {/* ---- Top nav ---- */}
      <header className="flex items-center justify-between px-4 py-2.5 border-b border-slate-800 bg-slate-900/80 backdrop-blur-sm z-30">
        <div className="flex items-center gap-2">
          <Map className="h-5 w-5 text-indigo-400" aria-hidden />
          <span className="font-bold text-white tracking-tight">PathMakers</span>
          <span className="text-xs text-slate-500 hidden sm:block">
            — AI Learning Roadmap
          </span>
        </div>

        <div className="flex items-center gap-3">
          {phase === "canvas" && (
            <button
              onClick={() => setPhase("intake")}
              className="text-xs text-slate-400 hover:text-white transition-colors px-3 py-1.5 rounded-lg border border-slate-700 hover:border-slate-500"
            >
              New roadmap
            </button>
          )}
          <a
            href="https://github.com/kanak28T/PathMakers"
            target="_blank"
            rel="noopener noreferrer"
            className="text-slate-400 hover:text-white transition-colors"
            aria-label="View source on GitHub"
          >
            <GitBranch className="h-4 w-4" />
          </a>
        </div>
      </header>

      {/* ---- Canvas (always mounted, hidden behind intake overlay) ---- */}
      <div className="flex-1 relative overflow-hidden">
        {/* Empty-state hint when canvas hasn't loaded yet */}
        {phase === "intake" && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none select-none">
            <div className="text-center space-y-2 opacity-20">
              <Map className="h-16 w-16 mx-auto text-slate-600" />
              <p className="text-slate-500 text-sm">
                Your roadmap will appear here
              </p>
            </div>
          </div>
        )}

        {phase === "canvas" && (
          <RoadmapCanvas intake={intake} />
        )}
      </div>

      {/* ---- Intake overlay ---- */}
      {phase === "intake" && (
        <IntakeDrawer onSubmit={handleIntakeSubmit} loading={loading} />
      )}
    </main>
  );
}
