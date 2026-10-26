"use client";

import { useId } from "react";

import { cn } from "./cn";

/** Full-width labelled checkbox with an optional detail line; the whole row is the target. */
export function CheckboxRow({
  label,
  detail,
  checked,
  onChange,
}: {
  label: string;
  detail?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  const id = useId();
  return (
    <label
      htmlFor={id}
      className={cn(
        "flex min-h-tap cursor-pointer items-start gap-3.5 rounded-tile p-4",
        checked ? "bg-selected ring-selected" : "bg-surface hairline",
      )}
    >
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        aria-describedby={detail ? `${id}-detail` : undefined}
        className="mt-0.5 size-5 shrink-0 accent-[var(--color-grad-to)]"
      />
      <span className="flex flex-col gap-0.5">
        <span className="text-[16px] leading-[22px] font-semibold">{label}</span>
        {detail && (
          <span id={`${id}-detail`} className="text-small leading-5 text-muted">
            {detail}
          </span>
        )}
      </span>
    </label>
  );
}
