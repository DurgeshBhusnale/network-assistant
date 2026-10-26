"use client";

import { useId } from "react";

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
      className="flex min-h-tap cursor-pointer items-start gap-3 rounded-card border border-line bg-surface p-card"
    >
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        aria-describedby={detail ? `${id}-detail` : undefined}
        className="mt-0.5 size-5 shrink-0 accent-[var(--color-primary)]"
      />
      <span className="flex flex-col gap-0.5">
        <span className="text-body font-semibold">{label}</span>
        {detail && (
          <span id={`${id}-detail`} className="text-small text-muted">
            {detail}
          </span>
        )}
      </span>
    </label>
  );
}
