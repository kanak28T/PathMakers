"use client";
/**
 * hooks/useGraphPatch.ts
 * SSE listener for Phase 4 graph patches.
 *
 * Opens /api/roadmap/stream/{learner_id} and calls onPatch whenever
 * the backend emits a "graph_patch" event.
 * Re-connects automatically on close unless the component unmounts.
 */

import { useEffect, useRef } from "react";
import type { RoadmapPatchEvent } from "@/lib/types";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function useGraphPatch(
  learnerId: string | null,
  onPatch: (patch: RoadmapPatchEvent) => void
) {
  const onPatchRef = useRef(onPatch);
  onPatchRef.current = onPatch; // always latest without re-subscribing

  useEffect(() => {
    if (!learnerId) return;

    let es: EventSource | null = null;
    let destroyed = false;

    function connect() {
      if (destroyed) return;
      es = new EventSource(
        `${BASE}/api/roadmap/stream/${encodeURIComponent(learnerId as string)}`
      );

      es.addEventListener("graph_patch", (e: MessageEvent) => {
        try {
          const patch = JSON.parse(e.data) as RoadmapPatchEvent;
          onPatchRef.current(patch);
        } catch {
          console.error("useGraphPatch: failed to parse patch event", e.data);
        }
      });

      es.onerror = () => {
        es?.close();
        // Back-off reconnect after 3 s
        if (!destroyed) setTimeout(connect, 3000);
      };
    }

    connect();

    return () => {
      destroyed = true;
      es?.close();
    };
  }, [learnerId]);
}
