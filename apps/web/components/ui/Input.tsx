"use client";

import { useId, type InputHTMLAttributes } from "react";

import { cn } from "./cn";

export type InputProps = Omit<InputHTMLAttributes<HTMLInputElement>, "id"> & {
  label: string;
  hint?: string;
  error?: string;
};

export function Input({ label, hint, error, className, ...rest }: InputProps) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className="text-small font-semibold text-ink">
        {label}
      </label>
      <input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        className={cn(
          "h-field rounded-button bg-surface px-4 text-[16px] text-ink placeholder:text-muted",
          "focus:shadow-[inset_0_0_0_1.5px_var(--color-primary-ring)] focus:outline-none",
          error ? "shadow-[inset_0_0_0_1.5px_var(--color-danger)]" : "hairline-strong",
          className,
        )}
        {...rest}
      />
      {hint && (
        <p id={hintId} className="text-caption text-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className="text-caption text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
