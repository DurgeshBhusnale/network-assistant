"use client";

import { useId } from "react";

export type StepperProps = {
  label: string;
  value: number;
  min: number;
  max: number;
  onChange: (value: number) => void;
  decreaseLabel?: string;
  increaseLabel?: string;
};

/** Label on the left, "− value +" pill on the right (v4). Buttons are 48 px wide. */
export function Stepper({
  label,
  value,
  min,
  max,
  onChange,
  decreaseLabel = "Fewer",
  increaseLabel = "More",
}: StepperProps) {
  const id = useId();
  const buttonClass =
    "inline-flex h-12 w-12 items-center justify-center rounded-pill text-[22px] text-ink-2 disabled:cursor-not-allowed disabled:opacity-40";

  return (
    <div role="group" aria-labelledby={id} className="flex items-center justify-between gap-3">
      <span id={id} className="text-small font-semibold text-ink">
        {label}
      </span>
      <div className="flex h-12 items-center rounded-pill bg-surface hairline-strong">
        <button
          type="button"
          aria-label={decreaseLabel}
          className={buttonClass}
          disabled={value <= min}
          onClick={() => onChange(Math.max(min, value - 1))}
        >
          −
        </button>
        <output aria-live="polite" className="w-7 text-center text-[18px] font-semibold">
          {value}
        </output>
        <button
          type="button"
          aria-label={increaseLabel}
          className={buttonClass}
          disabled={value >= max}
          onClick={() => onChange(Math.min(max, value + 1))}
        >
          +
        </button>
      </div>
    </div>
  );
}
