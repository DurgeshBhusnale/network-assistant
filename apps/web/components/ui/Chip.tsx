import type { ReactNode } from "react";

import { cn } from "./cn";

export type ChipTone = "highlight" | "neutral";

const tones: Record<ChipTone, string> = {
  highlight: "bg-primary-soft text-primary",
  neutral: "bg-surface-2 text-ink-2",
};

/** Reason tags on Today cards and similar short labels. */
export function Chip({ tone = "neutral", children }: { tone?: ChipTone; children: ReactNode }) {
  return (
    <span
      className={cn(
        "inline-flex rounded-[14px] px-3 py-[5px] text-caption leading-[18px]",
        tones[tone],
      )}
    >
      {children}
    </span>
  );
}
