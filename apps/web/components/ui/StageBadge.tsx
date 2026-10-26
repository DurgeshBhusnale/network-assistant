import { cn } from "./cn";

/**
 * Tone comes from the pack's stage config, not the stage id (ADR-0006):
 * a stage with an ask → "ask"; the closing thank-you stage → "thanks"; other stages → "nurture".
 */
export type StageTone = "ask" | "nurture" | "thanks";

const tones: Record<StageTone, string> = {
  ask: "bg-primary-soft text-primary",
  nurture: "bg-success-soft text-success",
  thanks: "bg-accent-soft text-accent-text",
};

export function StageBadge({ tone, label }: { tone: StageTone; label: string }) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 rounded-badge px-2 py-[3px] text-tiny font-semibold",
        tones[tone],
      )}
    >
      {label}
    </span>
  );
}
