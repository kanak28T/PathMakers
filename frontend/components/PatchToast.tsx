"use client";
/**
 * components/PatchToast.tsx
 * Light-theme SSE patch notification toast.
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
    if (!message) { setVisible(false); return; }
    setVisible(true);
    const t = setTimeout(() => {
      setVisible(false);
      setTimeout(onDismiss, 300);
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
        bg-white border border-blue-200 rounded-xl px-4 py-3 shadow-xl
        transition-all duration-300
        ${visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4 pointer-events-none"}
      `}
    >
      <div className="flex items-center justify-center h-7 w-7 rounded-lg bg-blue-100 shrink-0 mt-0.5">
        <Zap className="h-4 w-4 text-blue-600" aria-hidden />
      </div>
      <p className="flex-1 text-sm text-gray-700 leading-snug">{message}</p>
      <button
        onClick={() => { setVisible(false); setTimeout(onDismiss, 300); }}
        className="text-gray-400 hover:text-gray-700 transition-colors shrink-0"
        aria-label="Dismiss"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
