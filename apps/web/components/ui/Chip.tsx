import type { ReactNode } from "react";

import { cn } from "./cn";

export type ChipTone = "highlight" | "neutral";

const tones: Record<ChipTone, string> = {
  highlight: "bg-accent-soft text-accent-text",
  neutral: "bg-bg text-ink-2",
};

/** Reason chips on Today cards and similar short labels. */
export function Chip({ tone = "neutral", children }: { tone?: ChipTone; children: ReactNode }) {
  return (
    <span className={cn("inline-flex rounded-pill px-2 py-[3px] text-caption", tones[tone])}>
      {children}
    </span>
  );
}
