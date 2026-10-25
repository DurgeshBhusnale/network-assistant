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

/** "− value +" in a 46 px field. Buttons are 44 px (the design's 38 px is below the touch minimum). */
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
    "inline-flex size-tap items-center justify-center rounded-[8px] bg-bg text-[18px] text-ink disabled:cursor-not-allowed disabled:opacity-40";

  return (
    <div role="group" aria-labelledby={id} className="flex flex-col gap-1.5">
      <span id={id} className="text-small font-semibold">
        {label}
      </span>
      <div className="flex min-h-[46px] items-center justify-between rounded-button border border-line-strong bg-surface px-1">
        <button
          type="button"
          aria-label={decreaseLabel}
          className={buttonClass}
          disabled={value <= min}
          onClick={() => onChange(Math.max(min, value - 1))}
        >
          −
        </button>
        <output aria-live="polite" className="text-body font-semibold">
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
