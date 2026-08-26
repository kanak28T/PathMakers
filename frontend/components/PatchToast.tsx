"use client";
/**
 * components/PatchToast.tsx
 * Temporary toast that surfaces the patch summary from Phase 4 SSE events.
 */

import { useEffect, useState } from "react";
import { Zap, X } from "lucide-react";

interface Props {
  message: string | null;
  onDismiss: () => void;
}

export default function PatchToast({ message, onDismiss }: Props) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!message) {
      setVisible(false);
      return;
    }
    setVisible(true);
    const t = setTimeout(() => {
      setVisible(false);
      setTimeout(onDismiss, 300); // let the fade-out complete first
    }, 5000);
    return () => clearTimeout(t);
  }, [message, onDismiss]);

  return (
    <div
      role="status"
      aria-live="polite"
      className={`
        fixed bottom-6 left-1/2 -translate-x-1/2 z-50
        flex items-start gap-3 max-w-sm w-full
        bg-indigo-900/95 border border-indigo-500/50 rounded-xl px-4 py-3 shadow-2xl
        transition-all duration-300
        ${visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4 pointer-events-none"}
      `}
    >
      <Zap className="h-5 w-5 text-indigo-300 shrink-0 mt-0.5" aria-hidden />
      <p className="flex-1 text-sm text-indigo-100">{message}</p>
      <button
        onClick={() => { setVisible(false); setTimeout(onDismiss, 300); }}
        className="text-indigo-400 hover:text-white transition-colors"
        aria-label="Dismiss notification"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
