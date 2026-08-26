"use client";
/**
 * components/IntakeDrawer.tsx
 * roadmap.sh-style modal onboarding.
 * Light, clean, accessible — 4 steps.
 */

import { useState } from "react";
import {
  ChevronRight, ChevronLeft, Sparkles, Loader2,
  Target, Brain, Clock, CheckCircle2,
} from "lucide-react";
import type { LearnerIntakeForm } from "@/lib/types";

const ROLES = [
  { key: "ai_ml_engineer",     label: "AI / ML Engineer",    icon: "🤖" },
  { key: "data_scientist",     label: "Data Scientist",       icon: "📊" },
  { key: "data_engineer",      label: "Data Engineer",        icon: "🔧" },
  { key: "frontend_developer", label: "Frontend Developer",   icon: "🖥️" },
  { key: "backend_developer",  label: "Backend Developer",    icon: "⚙️" },
];

const SKILL_POOL = [
  "Python","JavaScript","TypeScript","SQL","Statistics",
  "Linear Algebra","Machine Learning","Deep Learning","Data Analysis",
  "React","Node.js","Docker","Git","Cloud Platforms",
];

const STEPS = [
  { id: "Goal",       icon: Target,        desc: "Pick your career goal" },
  { id: "Skills",     icon: Brain,         desc: "What you already know" },
  { id: "Pace",       icon: Clock,         desc: "Your availability" },
  { id: "Review",     icon: CheckCircle2,  desc: "Confirm & generate" },
];

interface Props {
  onSubmit: (form: LearnerIntakeForm) => void;
  loading: boolean;
}

export default function IntakeDrawer({ onSubmit, loading }: Props) {
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<LearnerIntakeForm>({
    name: "", target_role: "", self_reported_skills: [],
    experience_years: 0, weekly_hours: 10,
  });

  const toggleSkill = (skill: string) =>
    setForm((f) => ({
      ...f,
      self_reported_skills: f.self_reported_skills.includes(skill)
        ? f.self_reported_skills.filter((s) => s !== skill)
        : [...f.self_reported_skills, skill],
    }));

  const canNext =
    (step === 0 && !!form.name.trim() && !!form.target_role) ||
    step === 1 || step === 2 || step === 3;

  const StepIcon = STEPS[step].icon;

  return (
    /* Full-screen backdrop */
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/30 backdrop-blur-[2px]"
      role="dialog"
      aria-modal="true"
      aria-label="Set up your learning path"
    >
      <div className="animate-slide-up w-full max-w-lg bg-white rounded-2xl shadow-2xl border border-gray-200 overflow-hidden">

        {/* ── Step progress strip ── */}
        <div className="flex border-b border-gray-100">
          {STEPS.map((s, i) => {
            const Icon = s.icon;
            const active = i === step;
            const done   = i < step;
            return (
              <div
                key={s.id}
                className={`flex-1 flex flex-col items-center py-3 gap-1 text-center border-b-2 transition-colors ${
                  active ? "border-blue-600 bg-blue-50/60" :
                  done   ? "border-emerald-400 bg-emerald-50/40" :
                           "border-transparent"
                }`}
              >
                <Icon className={`h-4 w-4 ${active ? "text-blue-600" : done ? "text-emerald-500" : "text-gray-300"}`} />
                <span className={`text-[10px] font-semibold uppercase tracking-wide ${
                  active ? "text-blue-600" : done ? "text-emerald-600" : "text-gray-400"
                }`}>{s.id}</span>
              </div>
            );
          })}
        </div>

        <div className="p-6">

          {/* Step heading */}
          <div className="flex items-center gap-2 mb-5">
            <div className="flex items-center justify-center h-8 w-8 rounded-lg bg-blue-100">
              <StepIcon className="h-4 w-4 text-blue-600" />
            </div>
            <p className="text-sm text-gray-500">{STEPS[step].desc}</p>
          </div>

          {/* ── Step 0: Name + Role ── */}
          {step === 0 && (
            <div className="space-y-5">
              <div>
                <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1.5">
                  Your name
                </label>
                <input
                  id="name"
                  type="text"
                  autoFocus
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="e.g. Alex"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-700 mb-2">Target role</p>
                <div className="grid grid-cols-1 gap-2">
                  {ROLES.map((r) => (
                    <button
                      key={r.key}
                      onClick={() => setForm({ ...form, target_role: r.key })}
                      className={`flex items-center gap-3 text-left px-4 py-3 rounded-lg border text-sm font-medium transition-all ${
                        form.target_role === r.key
                          ? "border-blue-500 bg-blue-50 text-blue-800 shadow-sm"
                          : "border-gray-200 text-gray-700 hover:border-blue-300 hover:bg-gray-50"
                      }`}
                    >
                      <span className="text-lg">{r.icon}</span>
                      {r.label}
                      {form.target_role === r.key && (
                        <CheckCircle2 className="ml-auto h-4 w-4 text-blue-500" />
                      )}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ── Step 1: Skills ── */}
          {step === 1 && (
            <div className="space-y-4">
              <p className="text-sm text-gray-600">
                Pick skills you already know. No worries if you skip — the diagnostic quiz calibrates your baseline.
              </p>
              <div className="flex flex-wrap gap-2">
                {SKILL_POOL.map((skill) => {
                  const sel = form.self_reported_skills.includes(skill);
                  return (
                    <button
                      key={skill}
                      onClick={() => toggleSkill(skill)}
                      aria-pressed={sel}
                      className={`text-sm px-3 py-1.5 rounded-full border font-medium transition-all ${
                        sel
                          ? "border-blue-500 bg-blue-600 text-white shadow-sm"
                          : "border-gray-200 bg-white text-gray-600 hover:border-blue-300 hover:text-blue-700"
                      }`}
                    >
                      {skill}
                    </button>
                  );
                })}
              </div>
              {form.self_reported_skills.length > 0 && (
                <p className="text-xs text-blue-600 font-medium">
                  {form.self_reported_skills.length} skill{form.self_reported_skills.length > 1 ? "s" : ""} selected
                </p>
              )}
            </div>
          )}

          {/* ── Step 2: Pace ── */}
          {step === 2 && (
            <div className="space-y-5">
              <div>
                <label htmlFor="exp" className="block text-sm font-medium text-gray-700 mb-1.5">
                  Years of relevant experience
                </label>
                <input
                  id="exp"
                  type="number"
                  min={0} max={30} step={0.5}
                  value={form.experience_years}
                  onChange={(e) => setForm({ ...form, experience_years: Number(e.target.value) })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                />
              </div>
              <div>
                <div className="flex justify-between text-sm font-medium text-gray-700 mb-2">
                  <label htmlFor="weekly">Hours per week</label>
                  <span className="text-blue-600 font-bold">{form.weekly_hours}h</span>
                </div>
                <input
                  id="weekly"
                  type="range"
                  min={2} max={40} step={1}
                  value={form.weekly_hours}
                  onChange={(e) => setForm({ ...form, weekly_hours: Number(e.target.value) })}
                  className="w-full h-2 rounded-full accent-blue-600 cursor-pointer"
                />
                <div className="flex justify-between text-xs text-gray-400 mt-1">
                  <span>2h / week</span>
                  <span>40h / week</span>
                </div>
              </div>
              <div className="bg-blue-50 border border-blue-100 rounded-lg p-3 text-xs text-blue-700">
                💡 At {form.weekly_hours}h/week your roadmap will adapt its node spacing to your available time.
              </div>
            </div>
          )}

          {/* ── Step 3: Review ── */}
          {step === 3 && (
            <div className="space-y-4">
              <div className="bg-gray-50 border border-gray-200 rounded-xl divide-y divide-gray-100 overflow-hidden">
                {[
                  ["Name",       form.name],
                  ["Target role", ROLES.find((r) => r.key === form.target_role)?.label ?? "—"],
                  ["Skills",     form.self_reported_skills.length
                    ? form.self_reported_skills.join(", ")
                    : "None selected — quiz will calibrate"],
                  ["Experience", `${form.experience_years} year${form.experience_years !== 1 ? "s" : ""}`],
                  ["Weekly hours", `${form.weekly_hours}h / week`],
                ].map(([label, val]) => (
                  <div key={label} className="flex justify-between gap-4 px-4 py-2.5 text-sm">
                    <span className="text-gray-500 shrink-0">{label}</span>
                    <span className="text-gray-900 font-medium text-right">{val}</span>
                  </div>
                ))}
              </div>
              <p className="text-xs text-gray-500 text-center">
                Your roadmap is generated by our AI engine and adapts as you learn.
              </p>
            </div>
          )}

          {/* ── Navigation ── */}
          <div className="flex items-center justify-between mt-6 pt-4 border-t border-gray-100">
            <button
              onClick={() => setStep((s) => s - 1)}
              disabled={step === 0}
              className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors font-medium"
            >
              <ChevronLeft className="h-4 w-4" />
              Back
            </button>

            {step < STEPS.length - 1 ? (
              <button
                onClick={() => setStep((s) => s + 1)}
                disabled={!canNext}
                className="flex items-center gap-1.5 text-sm bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed text-white px-5 py-2.5 rounded-lg font-semibold transition-colors shadow-sm"
              >
                Continue
                <ChevronRight className="h-4 w-4" />
              </button>
            ) : (
              <button
                onClick={() => onSubmit(form)}
                disabled={loading}
                className="flex items-center gap-2 text-sm bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-5 py-2.5 rounded-lg font-semibold transition-colors shadow-sm"
              >
                {loading ? (
                  <><Loader2 className="h-4 w-4 animate-spin" /> Generating roadmap…</>
                ) : (
                  <><Sparkles className="h-4 w-4" /> Generate my roadmap</>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
