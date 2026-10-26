"use client";

import { useId, useRef, useState, type KeyboardEvent } from "react";

export type ChipInputProps = {
  label: string;
  values: string[];
  onChange: (values: string[]) => void;
  max?: number;
  addLabel: string;
  inputLabel: string;
  removeLabel: (value: string) => string;
  hint?: string;
  error?: string;
};

/** Chips + dashed "+ Add" chip (companies, locations). Enter or comma adds; duplicates ignored. */
export function ChipInput({
  label,
  values,
  onChange,
  max,
  addLabel,
  inputLabel,
  removeLabel,
  hint,
  error,
}: ChipInputProps) {
  const id = useId();
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const full = max !== undefined && values.length >= max;

  function commit() {
    const value = draft.trim();
    setDraft("");
    if (!value || full) return;
    if (values.some((v) => v.toLowerCase() === value.toLowerCase())) return;
    onChange([...values, value]);
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      commit();
    } else if (event.key === "Escape") {
      setDraft("");
      setAdding(false);
    }
  }

  return (
    <div role="group" aria-labelledby={`${id}-label`} className="flex flex-col gap-2.5">
      <span id={`${id}-label`} className="text-small font-semibold text-ink">
        {label}
      </span>
      <div className="flex flex-wrap items-center gap-2">
        {values.map((value) => (
          <span
            key={value}
            className="inline-flex h-10 items-center gap-0.5 rounded-pill bg-primary-soft pr-1 pl-4 text-small font-semibold text-primary"
          >
            {value}
            <button
              type="button"
              aria-label={removeLabel(value)}
              onClick={() => onChange(values.filter((v) => v !== value))}
              className="inline-flex size-8 items-center justify-center rounded-pill text-[16px]"
            >
              ×
            </button>
          </span>
        ))}
        {adding && !full ? (
          <input
            ref={inputRef}
            aria-label={inputLabel}
            value={draft}
            autoFocus
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={onKeyDown}
            onBlur={() => {
              commit();
              setAdding(false);
            }}
            className="h-10 min-w-[140px] flex-1 rounded-pill bg-surface px-4 text-[15px] shadow-[inset_0_0_0_1.5px_var(--color-primary-ring)] focus:outline-none"
          />
        ) : (
          !full && (
            <button
              type="button"
              onClick={() => setAdding(true)}
              className="h-10 rounded-pill bg-transparent px-4 text-small font-semibold text-primary shadow-[inset_0_0_0_1px_var(--color-line-accent)]"
            >
              {addLabel}
            </button>
          )
        )}
      </div>
      {hint && !error && <p className="text-caption text-muted">{hint}</p>}
      {error && <p className="text-caption text-danger">{error}</p>}
    </div>
  );
}
