/**
 * lib/api.ts
 * All backend API calls. Reads NEXT_PUBLIC_API_BASE_URL from .env.local.
 * Frontend → Backend contract surface.
 */

import type {
  RoadmapGraphResponse,
  RoadmapPatchEvent,
  RecalibrateRequest,
  LearnerIntakeForm,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Fetch the mock roadmap (Day-1 stable build target)
// ---------------------------------------------------------------------------
export async function fetchMockRoadmap(): Promise<RoadmapGraphResponse> {
  const res = await fetch(`${BASE}/api/roadmap/mock`);
  if (!res.ok) throw new Error(`fetchMockRoadmap: ${res.status}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// Generate a real roadmap from a learner profile (Day-4+ live)
// ---------------------------------------------------------------------------
export async function generateRoadmap(
  profile: LearnerIntakeForm & { learner_id: string }
): Promise<RoadmapGraphResponse> {
  const res = await fetch(`${BASE}/api/roadmap/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile),
  });
  if (!res.ok) {
    // Graceful fallback to mock so the UI never breaks without a live backend
    console.warn("generateRoadmap failed, falling back to mock");
    return fetchMockRoadmap();
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Send a recalibrate signal (Phase 4)
// ---------------------------------------------------------------------------
export async function recalibrateRoadmap(
  req: RecalibrateRequest
): Promise<RoadmapPatchEvent> {
  const res = await fetch(`${BASE}/api/roadmap/recalibrate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    // Return the canonical mock patch so the UI can still demo the animation
    const mock = await fetch(`${BASE}/api/roadmap/patch/mock`);
    return mock.json();
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Fetch the mock patch (used during development)
// ---------------------------------------------------------------------------
export async function fetchMockPatch(): Promise<RoadmapPatchEvent> {
  const res = await fetch(`${BASE}/api/roadmap/patch/mock`);
  if (!res.ok) throw new Error(`fetchMockPatch: ${res.status}`);
  return res.json();
}
