"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { ApiError } from "@/lib/api/client";
import { useSaveStyle, type Style } from "@/lib/api/hooks/drafts";
import { copy } from "@/lib/copy/en";

const t = copy.style;
const MIN_SAMPLES = 3;
const MAX_SAMPLES = 10;

function split(value: string): string[] {
  return value
    .split(/\n\s*\n/)
    .map((s) => s.trim())
    .filter(Boolean)
    .slice(0, MAX_SAMPLES);
}

/** Paste 3–10 sent messages; the API summarises them into a style the drafts follow. */
export function StyleForm({
  initial,
  onSaved,
}: {
  initial: Style | undefined;
  onSaved?: () => void;
}) {
  const save = useSaveStyle();
  const [value, setValue] = useState((initial?.samples ?? []).join("\n\n"));
  const samples = split(value);

  async function submit() {
    try {
      await save.mutateAsync(samples);
      onSaved?.();
    } catch {
      // Shown below from the mutation state.
    }
  }

  const summary = save.data?.summary ?? initial?.summary;
  return (
    <div className="flex flex-col gap-3">
      <p className="text-body text-ink-2">{t.body}</p>
      <label htmlFor="style-samples" className="text-small font-semibold">
        {t.label}
      </label>
      <textarea
        id="style-samples"
        rows={10}
        value={value}
        placeholder={t.placeholder}
        onChange={(e) => setValue(e.target.value)}
        aria-describedby="style-count"
        className="rounded-button border border-line-strong bg-surface p-3 text-body"
      />
      <span id="style-count" className="text-caption text-muted">
        {t.count(samples.length)}
        {samples.length > 0 && samples.length < MIN_SAMPLES ? ` · ${t.tooFew}` : ""}
      </span>
      {save.error && (
        <p role="alert" className="text-small text-danger">
          {save.error instanceof ApiError ? save.error.message : copy.common.genericError}
        </p>
      )}
      <Button
        size="lg"
        fullWidth
        loading={save.isPending}
        disabled={samples.length < MIN_SAMPLES}
        onClick={() => void submit()}
      >
        {t.save}
      </Button>
      {summary && (
        <div className="flex flex-col gap-1 rounded-card bg-primary-soft p-card">
          <span className="text-small font-semibold text-primary">{t.summaryTitle}</span>
          <span className="text-small text-ink">{summary}</span>
        </div>
      )}
    </div>
  );
}
