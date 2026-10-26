import { copy } from "@/lib/copy/en";

import { cn } from "./cn";

/** 3-segment bar + "Step N of 3" (onboarding). */
export function ProgressSteps({ step, total = 3 }: { step: number; total?: number }) {
  const label = copy.common.stepOf(step, total);
  return (
    <div className="flex flex-col gap-2">
      <div role="img" aria-label={label} className="flex gap-1.5">
        {Array.from({ length: total }, (_, i) => (
          <div
            key={i}
            className={cn("h-1 flex-1 rounded-pill", i < step ? "bg-primary" : "bg-line")}
          />
        ))}
      </div>
      <span className="text-small text-muted" aria-hidden="true">
        {label}
      </span>
    </div>
  );
}
