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
    <div role="group" aria-labelledby={`${id}-label`} className="flex flex-col gap-1.5">
      <span id={`${id}-label`} className="text-small font-semibold">
        {label}
      </span>
      <div className="flex flex-wrap items-center gap-1.5">
        {values.map((value) => (
          <span
            key={value}
            className="inline-flex min-h-tap items-center gap-1 rounded-pill bg-primary-soft pr-1 pl-3 text-small font-semibold text-primary"
          >
            {value}
            <button
              type="button"
              aria-label={removeLabel(value)}
              onClick={() => onChange(values.filter((v) => v !== value))}
              className="inline-flex size-9 items-center justify-center rounded-pill text-[16px]"
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
            className="h-tap min-w-[140px] flex-1 rounded-pill border border-line-strong bg-surface px-3 text-body"
          />
        ) : (
          !full && (
            <button
              type="button"
              onClick={() => setAdding(true)}
              className="min-h-tap rounded-pill border border-dashed border-primary bg-transparent px-3 text-small font-semibold text-primary"
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
