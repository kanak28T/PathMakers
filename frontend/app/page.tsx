/**
 * app/page.tsx
 * roadmap.sh-inspired landing → roadmap canvas.
 * RoadmapCanvas must be SSR-disabled (React Flow uses browser APIs).
 */

"use client";

import dynamic from "next/dynamic";
import { useState, useCallback } from "react";
import {
  Map, GitBranch, Sparkles, ChevronRight,
  BookOpen, BarChart2, Zap, Users,
} from "lucide-react";
import IntakeDrawer from "@/components/IntakeDrawer";
import type { LearnerIntakeForm } from "@/lib/types";
import { generateRoadmap } from "@/lib/api";

const RoadmapCanvas = dynamic(() => import("@/components/RoadmapCanvas"), { ssr: false });

type Phase = "landing" | "intake" | "canvas";

const FEATURE_CARDS = [
  {
    icon: BarChart2,
    title: "AI-Ranked Courses",
    desc: "A trained ML model scores every course against your skill gaps, not arbitrary weights.",
    color: "text-blue-600",
    bg: "bg-blue-50",
  },
  {
    icon: Zap,
    title: "Adaptive Recalibration",
    desc: "Fail a quiz or skip a node and the roadmap re-routes in real time via Phase 4 diff.",
    color: "text-amber-600",
    bg: "bg-amber-50",
  },
  {
    icon: BookOpen,
    title: "Prerequisite-Aware DAG",
    desc: "Courses are sequenced using topological sort — no more jumping into advanced content blind.",
    color: "text-emerald-600",
    bg: "bg-emerald-50",
  },
  {
    icon: Users,
    title: "XAI Node Inspector",
    desc: "Click any node to see why the AI recommended it — SHAP feature-importance bars included.",
    color: "text-violet-600",
    bg: "bg-violet-50",
  },
];

export default function HomePage() {
  const [phase, setPhase] = useState<Phase>("landing");
  const [loading, setLoading] = useState(false);
  const [intake, setIntake] = useState<
    (LearnerIntakeForm & { learner_id: string }) | undefined
  >(undefined);

  const handleIntakeSubmit = useCallback(async (form: LearnerIntakeForm) => {
    setLoading(true);
    const full = { ...form, learner_id: `learner_${Date.now()}` };
    try { await generateRoadmap(full); } catch { /* falls back to mock */ }
    setIntake(full);
    setLoading(false);
    setPhase("canvas");
  }, []);

  return (
    <div className="flex flex-col min-h-screen bg-white">

      {/* ══════════════ NAVBAR ══════════════ */}
      <header className="sticky top-0 z-30 bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto flex items-center justify-between px-5 h-14">
          {/* Logo */}
          <button
            onClick={() => setPhase("landing")}
            className="flex items-center gap-2 group"
            aria-label="PathMakers home"
          >
            <div className="flex items-center justify-center h-7 w-7 rounded-lg bg-blue-600 group-hover:bg-blue-700 transition-colors">
              <Map className="h-4 w-4 text-white" aria-hidden />
            </div>
            <span className="font-bold text-gray-900 text-[15px]">PathMakers</span>
          </button>

          {/* Nav links */}
          <nav className="hidden sm:flex items-center gap-6 text-sm text-gray-600">
            <a href="#features" className="hover:text-blue-600 transition-colors">Features</a>
            <a href="#how" className="hover:text-blue-600 transition-colors">How it works</a>
            <a
              href="https://github.com/kanak28T/PathMakers"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-blue-600 transition-colors flex items-center gap-1"
            >
              <GitBranch className="h-3.5 w-3.5" aria-hidden />
              GitHub
            </a>
          </nav>

          {/* CTA */}
          {phase !== "canvas" ? (
            <button
              onClick={() => setPhase("intake")}
              className="flex items-center gap-1.5 text-sm bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-semibold transition-colors shadow-sm"
            >
              <Sparkles className="h-3.5 w-3.5" aria-hidden />
              Get started
            </button>
          ) : (
            <button
              onClick={() => setPhase("intake")}
              className="text-sm text-gray-600 hover:text-blue-600 px-3 py-1.5 rounded-lg border border-gray-200 hover:border-blue-300 transition-colors font-medium"
            >
              New roadmap
            </button>
          )}
        </div>
      </header>

      {/* ══════════════ CANVAS VIEW ══════════════ */}
      {phase === "canvas" && (
        <main className="flex-1 overflow-hidden" style={{ height: "calc(100vh - 56px)" }}>
          <RoadmapCanvas intake={intake} />
        </main>
      )}

      {/* ══════════════ LANDING VIEW ══════════════ */}
      {phase !== "canvas" && (
        <main className="flex-1">

          {/* ── Hero ── */}
          <section className="max-w-6xl mx-auto px-5 pt-20 pb-16 text-center">
            <div className="inline-flex items-center gap-2 bg-blue-50 border border-blue-100 text-blue-700 text-xs font-semibold px-3 py-1.5 rounded-full mb-6">
              <Sparkles className="h-3.5 w-3.5" aria-hidden />
              AI-Powered · Prerequisite-Aware · Adaptive
            </div>

            <h1 className="text-4xl sm:text-5xl font-extrabold text-gray-900 leading-tight tracking-tight mb-5">
              Your personal learning<br />
              <span className="text-blue-600">roadmap, built by AI</span>
            </h1>

            <p className="text-lg text-gray-500 max-w-2xl mx-auto mb-8 leading-relaxed">
              PathMakers generates a course-by-course, prerequisite-sequenced
              flowchart tailored to your career goal — and recalibrates in real
              time as you learn.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              <button
                onClick={() => setPhase("intake")}
                className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-xl font-semibold text-sm transition-colors shadow-sm"
              >
                <Sparkles className="h-4 w-4" aria-hidden />
                Build my roadmap
                <ChevronRight className="h-4 w-4" aria-hidden />
              </button>
              <a
                href="https://github.com/kanak28T/PathMakers"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 border border-gray-300 hover:border-gray-400 text-gray-700 px-6 py-3 rounded-xl font-semibold text-sm transition-colors"
              >
                <GitBranch className="h-4 w-4" aria-hidden />
                View on GitHub
              </a>
            </div>

            {/* Hero mockup strip */}
            <div className="mt-14 rounded-2xl border border-gray-200 shadow-xl overflow-hidden bg-gray-50 p-6">
              <div className="flex items-center gap-1.5 mb-4">
                <span className="w-3 h-3 rounded-full bg-red-400" />
                <span className="w-3 h-3 rounded-full bg-amber-400" />
                <span className="w-3 h-3 rounded-full bg-emerald-400" />
                <span className="ml-2 text-xs text-gray-400 font-medium">PathMakers — AI / ML Engineer</span>
              </div>
              {/* Fake flowchart preview */}
              <div className="flex flex-col items-center gap-2">
                {[
                  { label: "Python for Everybody",          status: "completed",   diff: "beginner" },
                  { label: "Mathematics for ML",            status: "completed",   diff: "intermediate" },
                  { label: "Data Analysis with Pandas",     status: "in_progress", diff: "intermediate" },
                  { label: "Machine Learning Specialization", status: "pending",   diff: "intermediate" },
                  { label: "Deep Learning Specialization",  status: "pending",     diff: "advanced" },
                ].map((n, i) => (
                  <div key={i} className="flex flex-col items-center">
                    <MockNode {...n} />
                    {i < 4 && <div className="w-px h-4 bg-gray-300" />}
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* ── Features ── */}
          <section id="features" className="bg-gray-50 border-t border-gray-100 py-16">
            <div className="max-w-6xl mx-auto px-5">
              <p className="text-xs font-semibold uppercase tracking-widest text-blue-600 text-center mb-2">
                What makes PathMakers different
              </p>
              <h2 className="text-2xl font-bold text-gray-900 text-center mb-10">
                Features built for serious learners
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
                {FEATURE_CARDS.map((f) => {
                  const Icon = f.icon;
                  return (
                    <div key={f.title} className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm hover:shadow-md transition-shadow">
                      <div className={`inline-flex items-center justify-center h-9 w-9 rounded-lg ${f.bg} mb-3`}>
                        <Icon className={`h-4.5 w-4.5 ${f.color}`} aria-hidden />
                      </div>
                      <h3 className="text-sm font-bold text-gray-900 mb-1">{f.title}</h3>
                      <p className="text-xs text-gray-500 leading-relaxed">{f.desc}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          </section>

          {/* ── How it works ── */}
          <section id="how" className="py-16">
            <div className="max-w-3xl mx-auto px-5 text-center">
              <h2 className="text-2xl font-bold text-gray-900 mb-3">
                How it works
              </h2>
              <p className="text-gray-500 text-sm mb-10">Three steps from goal to interactive flowchart.</p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 text-left">
                {[
                  { step: "01", title: "Set your goal",   desc: "Pick a career role and tell us what you already know. A short diagnostic quiz calibrates your baseline." },
                  { step: "02", title: "AI builds your path", desc: "Our ML model ranks courses by skill-gap fit and sequences them into a DAG using topological sort." },
                  { step: "03", title: "Learn & adapt",   desc: "Mark nodes complete, fail quizzes, or skip topics. The roadmap recalibrates with new remediation paths in real time." },
                ].map((item) => (
                  <div key={item.step} className="flex gap-4">
                    <div className="flex-shrink-0 flex items-center justify-center h-9 w-9 rounded-full bg-blue-600 text-white text-sm font-bold">
                      {item.step}
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-gray-900 mb-1">{item.title}</h3>
                      <p className="text-xs text-gray-500 leading-relaxed">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* ── CTA banner ── */}
          <section className="bg-blue-600 py-14">
            <div className="max-w-2xl mx-auto px-5 text-center">
              <h2 className="text-2xl font-bold text-white mb-3">
                Ready to map your learning journey?
              </h2>
              <p className="text-blue-100 text-sm mb-6">
                It takes 2 minutes. Your personalized roadmap is generated instantly.
              </p>
              <button
                onClick={() => setPhase("intake")}
                className="inline-flex items-center gap-2 bg-white text-blue-700 hover:bg-blue-50 font-bold px-7 py-3 rounded-xl text-sm transition-colors shadow"
              >
                <Sparkles className="h-4 w-4" aria-hidden />
                Get started — it's free
              </button>
            </div>
          </section>

          {/* ── Footer ── */}
          <footer className="border-t border-gray-200 py-8">
            <div className="max-w-6xl mx-auto px-5 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-gray-400">
              <div className="flex items-center gap-2">
                <Map className="h-3.5 w-3.5 text-blue-500" />
                <span className="font-semibold text-gray-600">PathMakers</span>
                <span>— AI Learning Roadmap</span>
              </div>
              <div className="flex items-center gap-4">
                <a href="https://github.com/kanak28T/PathMakers" target="_blank" rel="noopener noreferrer" className="hover:text-gray-700 transition-colors">GitHub</a>
                <span>Built for Hackathon 2026</span>
              </div>
            </div>
          </footer>
        </main>
      )}

      {/* ── Intake modal ── */}
      {phase === "intake" && (
        <IntakeDrawer onSubmit={handleIntakeSubmit} loading={loading} />
      )}
    </div>
  );
}

// ---- tiny mock node for hero preview ----
function MockNode({
  label, status, diff,
}: {
  label: string; status: string; diff: string;
}) {
  const accent: Record<string, string> = {
    completed:   "bg-emerald-500",
    in_progress: "bg-blue-500",
    pending:     "bg-gray-300",
  };
  const diffCls: Record<string, string> = {
    beginner:     "bg-emerald-100 text-emerald-700",
    intermediate: "bg-blue-100 text-blue-700",
    advanced:     "bg-purple-100 text-purple-700",
  };
  return (
    <div className="flex w-64 rounded-lg border border-gray-200 overflow-hidden shadow-sm bg-white">
      <div className={`w-1.5 shrink-0 ${accent[status] ?? "bg-gray-300"}`} />
      <div className="flex-1 px-3 py-2 flex items-center justify-between gap-2">
        <span className="text-xs font-semibold text-gray-800 truncate">{label}</span>
        <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full shrink-0 ${diffCls[diff]}`}>{diff}</span>
      </div>
    </div>
  );
}
