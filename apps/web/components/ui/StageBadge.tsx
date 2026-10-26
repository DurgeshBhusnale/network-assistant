import { cn } from "./cn";

/**
 * Tone comes from the pack's stage config, not the stage id (ADR-0006):
 * a stage with an ask → "ask"; the closing thank-you stage → "thanks"; other stages → "nurture".
 */
export type StageTone = "ask" | "nurture" | "thanks";

const tones: Record<StageTone, string> = {
  ask: "bg-primary-soft text-primary",
  nurture: "bg-badge-neutral text-badge-neutral-text",
  thanks: "bg-[var(--color-info-from)] text-info-text",
};

export function StageBadge({ tone, label }: { tone: StageTone; label: string }) {
  return (
    <span
      className={cn(
        "inline-flex h-6 shrink-0 items-center rounded-badge px-2.5 text-label font-semibold",
        tones[tone],
      )}
    >
      {label}
    </span>
  );
}
