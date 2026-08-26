"use client";
/**
 * components/IntakeDrawer.tsx
 * Step-by-step conversational onboarding drawer.
 * Collects: target role → self-reported skills → experience → weekly hours.
 * On submit fires generateRoadmap (with mock fallback built into api.ts).
 */

import { useState } from "react";
import { ChevronRight, ChevronLeft, Sparkles, Loader2 } from "lucide-react";
import type { LearnerIntakeForm } from "@/lib/types";

const ROLES = [
  { key: "ai_ml_engineer", label: "AI / ML Engineer" },
  { key: "data_scientist", label: "Data Scientist" },
  { key: "data_engineer", label: "Data Engineer" },
  { key: "frontend_developer", label: "Frontend Developer" },
  { key: "backend_developer", label: "Backend Developer" },
];

const SKILL_POOL = [
  "Python", "JavaScript", "TypeScript", "SQL", "Statistics",
  "Linear Algebra", "Machine Learning", "Deep Learning", "Data Analysis",
  "React", "Node.js", "Docker", "Git", "Cloud Platforms",
];

const STEPS = ["Goal", "Skills", "Experience", "Ready"];

interface Props {
  onSubmit: (form: LearnerIntakeForm) => void;
  loading: boolean;
}

export default function IntakeDrawer({ onSubmit, loading }: Props) {
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<LearnerIntakeForm>({
    name: "",
    target_role: "",
    self_reported_skills: [],
    experience_years: 0,
    weekly_hours: 10,
  });

  function toggleSkill(skill: string) {
    setForm((f) => ({
      ...f,
      self_reported_skills: f.self_reported_skills.includes(skill)
        ? f.self_reported_skills.filter((s) => s !== skill)
        : [...f.self_reported_skills, skill],
    }));
  }

  const canNext =
    (step === 0 && form.name.trim() && form.target_role) ||
    (step === 1) || // skills are optional
    (step === 2) ||
    step === 3;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Learning path setup"
    >
      <div className="w-full max-w-md bg-slate-900 rounded-2xl border border-slate-700 shadow-2xl overflow-hidden">
        {/* Progress bar */}
        <div className="h-1 bg-slate-800">
          <div
            className="h-full bg-indigo-500 transition-all duration-500"
            style={{ width: `${((step + 1) / STEPS.length) * 100}%` }}
          />
        </div>

        <div className="p-6">
          {/* Step indicator */}
          <div className="flex gap-1.5 mb-6">
            {STEPS.map((s, i) => (
              <span
                key={s}
                className={`text-[11px] px-2 py-0.5 rounded-full transition-colors ${
                  i === step
                    ? "bg-indigo-600 text-white"
                    : i < step
                    ? "bg-indigo-900 text-indigo-300"
                    : "bg-slate-800 text-slate-500"
                }`}
              >
                {s}
              </span>
            ))}
          </div>

          {/* ---- Step 0: Name + Role ---- */}
          {step === 0 && (
            <div className="space-y-4">
              <h2 className="text-xl font-bold text-white">
                What are you aiming for?
              </h2>
              <div>
                <label className="text-sm text-slate-400 mb-1 block" htmlFor="name">
                  Your name
                </label>
                <input
                  id="name"
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="e.g. Alex"
                  className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="text-sm text-slate-400 mb-1 block">
                  Target role
                </label>
                <div className="grid grid-cols-1 gap-2">
                  {ROLES.map((r) => (
                    <button
                      key={r.key}
                      onClick={() => setForm({ ...form, target_role: r.key })}
                      className={`text-left px-3 py-2.5 rounded-lg border text-sm transition-colors ${
                        form.target_role === r.key
                          ? "border-indigo-500 bg-indigo-900/40 text-indigo-200"
                          : "border-slate-700 text-slate-300 hover:border-slate-500"
                      }`}
                    >
                      {r.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ---- Step 1: Skills ---- */}
          {step === 1 && (
            <div className="space-y-4">
              <h2 className="text-xl font-bold text-white">
                What do you already know?
              </h2>
              <p className="text-sm text-slate-400">
                Select anything you're comfortable with. Skip if unsure — the
                diagnostic quiz will calibrate.
              </p>
              <div className="flex flex-wrap gap-2">
                {SKILL_POOL.map((skill) => (
                  <button
                    key={skill}
                    onClick={() => toggleSkill(skill)}
                    className={`text-sm px-3 py-1.5 rounded-full border transition-colors ${
                      form.self_reported_skills.includes(skill)
                        ? "border-indigo-500 bg-indigo-900/50 text-indigo-200"
                        : "border-slate-700 text-slate-400 hover:border-slate-500"
                    }`}
                    aria-pressed={form.self_reported_skills.includes(skill)}
                  >
                    {skill}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* ---- Step 2: Experience + time ---- */}
          {step === 2 && (
            <div className="space-y-5">
              <h2 className="text-xl font-bold text-white">
                Tell us about your pace
              </h2>

              <div>
                <label className="text-sm text-slate-400 mb-1 block" htmlFor="exp">
                  Years of relevant experience
                </label>
                <input
                  id="exp"
                  type="number"
                  min={0}
                  max={30}
                  step={0.5}
                  value={form.experience_years}
                  onChange={(e) =>
                    setForm({ ...form, experience_years: Number(e.target.value) })
                  }
                  className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="text-sm text-slate-400 mb-1 block" htmlFor="weekly">
                  Hours available per week:{" "}
                  <span className="text-indigo-300 font-medium">
                    {form.weekly_hours}h
                  </span>
                </label>
                <input
                  id="weekly"
                  type="range"
                  min={2}
                  max={40}
                  step={1}
                  value={form.weekly_hours}
                  onChange={(e) =>
                    setForm({ ...form, weekly_hours: Number(e.target.value) })
                  }
                  className="w-full accent-indigo-500"
                />
                <div className="flex justify-between text-xs text-slate-500 mt-0.5">
                  <span>2h</span>
                  <span>40h</span>
                </div>
              </div>
            </div>
          )}

          {/* ---- Step 3: Confirm ---- */}
          {step === 3 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-indigo-400" aria-hidden />
                <h2 className="text-xl font-bold text-white">You're all set</h2>
              </div>
              <ul className="text-sm text-slate-300 space-y-1.5">
                <li>
                  <span className="text-slate-500">Name:</span>{" "}
                  <span className="font-medium">{form.name}</span>
                </li>
                <li>
                  <span className="text-slate-500">Role:</span>{" "}
                  <span className="font-medium">
                    {ROLES.find((r) => r.key === form.target_role)?.label}
                  </span>
                </li>
                <li>
                  <span className="text-slate-500">Skills selected:</span>{" "}
                  <span className="font-medium">
                    {form.self_reported_skills.length || "None (quiz will calibrate)"}
                  </span>
                </li>
                <li>
                  <span className="text-slate-500">Experience:</span>{" "}
                  <span className="font-medium">{form.experience_years} years</span>
                </li>
                <li>
                  <span className="text-slate-500">Weekly hours:</span>{" "}
                  <span className="font-medium">{form.weekly_hours}h</span>
                </li>
              </ul>
              <p className="text-xs text-slate-500">
                Your learning roadmap will be generated by our AI engine. You
                can recalibrate it anytime from the canvas.
              </p>
            </div>
          )}

          {/* Navigation */}
          <div className="flex items-center justify-between mt-6">
            <button
              onClick={() => setStep((s) => s - 1)}
              disabled={step === 0}
              className="flex items-center gap-1 text-sm text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="h-4 w-4" />
              Back
            </button>

            {step < STEPS.length - 1 ? (
              <button
                onClick={() => setStep((s) => s + 1)}
                disabled={!canNext}
                className="flex items-center gap-1 text-sm bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg transition-colors"
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </button>
            ) : (
              <button
                onClick={() => onSubmit(form)}
                disabled={loading}
                className="flex items-center gap-2 text-sm bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white px-5 py-2 rounded-lg font-medium transition-colors"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4" />
                    Build my path
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
