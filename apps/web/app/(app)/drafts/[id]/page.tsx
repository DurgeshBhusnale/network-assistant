"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { SendPanel } from "@/components/drafts/SendPanel";
import { Button } from "@/components/ui/Button";
import { cn } from "@/components/ui/cn";
import { ApiError } from "@/lib/api/client";
import {
  useDraft,
  useEditDraft,
  useRegenerateDraft,
  type Draft,
  type Tone,
} from "@/lib/api/hooks/drafts";
import { usePerson } from "@/lib/api/hooks/people";
import { copy } from "@/lib/copy/en";

const t = copy.draft;
const TONES = Object.keys(t.tones) as Tone[];

function wordCount(text: string): number {
  return text.trim() ? text.trim().split(/\s+/).length : 0;
}

function DraftView({ draft }: { draft: Draft }) {
  const router = useRouter();
  const person = usePerson(draft.contact_id);
  const regenerate = useRegenerateDraft(draft.id);
  const edit = useEditDraft(draft.id);
  const serverText = draft.final_text ?? draft.text;
  const [text, setText] = useState(serverText);
  const [shownFor, setShownFor] = useState(serverText);

  // A regenerated draft replaces the editor text (render-time sync, no effect needed).
  if (serverText !== shownFor) {
    setShownFor(serverText);
    setText(serverText);
  }

  const p = person.data;
  const firstName = p?.first_name ?? p?.full_name.split(" ")[0] ?? "";
  const meta = p ? [p.title, p.company, p.how_known].filter(Boolean).join(" · ") : "";
  const busy = regenerate.isPending;
  const limitHit =
    regenerate.error instanceof ApiError && regenerate.error.status === 402
      ? regenerate.error
      : null;

  async function rewrite(tone: Tone | null) {
    try {
      await regenerate.mutateAsync(tone);
    } catch (e) {
      if (e instanceof ApiError && e.status === 402) router.push("/upgrade?reason=regen");
    }
  }

  async function saveEdit() {
    const trimmed = text.trim();
    if (trimmed && trimmed !== serverText.trim()) await edit.mutateAsync(trimmed);
  }

  return (
    <div className="flex flex-col gap-gap-cards px-screen-x pt-4">
      <div className="flex items-center gap-3">
        <button
          type="button"
          aria-label={t.back}
          onClick={() => router.back()}
          className="inline-flex size-tap shrink-0 items-center justify-center rounded-pill border border-line bg-surface"
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            aria-hidden="true"
          >
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </button>
        <div className="flex min-w-0 flex-col">
          <h1 className="m-0 truncate font-display text-h2 font-semibold">{p?.full_name ?? ""}</h1>
          {meta && <span className="truncate text-small text-muted">{meta}</span>}
        </div>
      </div>

      <span className="self-start rounded-badge bg-primary-soft px-2 py-[3px] text-tiny font-semibold text-primary">
        {t.stepBadge(draft.step, draft.total_steps, draft.stage_label)}
      </span>

      <div className="flex flex-col gap-2 rounded-card border border-line bg-surface p-card">
        <label htmlFor="draft-text" className="text-small font-semibold">
          {t.messageLabel}
        </label>
        <textarea
          id="draft-text"
          value={busy ? t.writing : text}
          readOnly={busy}
          aria-busy={busy}
          onChange={(e) => setText(e.target.value)}
          onBlur={() => void saveEdit()}
          rows={8}
          className={cn(
            "min-h-[196px] resize-none border-0 bg-transparent p-0 text-body leading-[1.55] text-ink",
            busy && "text-muted",
          )}
        />
        <div className="flex items-center justify-between gap-2">
          <span className="text-caption text-muted" aria-live="polite">
            {edit.isSuccess && !busy ? t.saved : t.meta(wordCount(text))}
          </span>
          <Button
            variant="ghost"
            className="px-2"
            disabled={busy}
            onClick={() => void rewrite(null)}
          >
            {t.anotherVersion}
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2" role="group" aria-label="Tone">
        {TONES.map((tone) => (
          <button
            key={tone}
            type="button"
            disabled={busy}
            aria-pressed={draft.tone === tone}
            onClick={() => void rewrite(tone)}
            className={cn(
              "min-h-tap rounded-pill border px-3 text-small font-semibold",
              draft.tone === tone
                ? "border-primary bg-primary-soft text-primary"
                : "border-line bg-surface text-ink-2",
            )}
          >
            {t.tones[tone]}
          </button>
        ))}
      </div>
      {draft.regenerations_left !== null && (
        <p className="text-caption text-muted">{t.rewritesLeft(draft.regenerations_left)}</p>
      )}

      {(draft.warnings.length > 0 || draft.unsupported_claims.length > 0) && (
        <div
          role="alert"
          className="flex flex-col gap-1.5 rounded-card bg-accent-soft p-card text-accent-text"
        >
          <span className="text-small font-semibold">{t.checkTitle}</span>
          {draft.unsupported_claims.length > 0 && (
            <>
              <span className="text-small">{t.unsupported}</span>
              <ul className="m-0 pl-5 text-small">
                {draft.unsupported_claims.map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
            </>
          )}
          {draft.warnings
            .filter((w) => w !== "unsupported_claims")
            .map((w) => (
              <span key={w} className="text-small">
                {t.warnings[w as keyof typeof t.warnings] ?? w}
              </span>
            ))}
        </div>
      )}

      {draft.reasons.length > 0 && (
        <div className="flex flex-col gap-1.5">
          <h2 className="m-0 text-small font-semibold">{t.whyTitle(firstName)}</h2>
          <ul className="m-0 pl-5 text-small text-ink-2">
            {draft.reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </div>
      )}

      <SendPanel draft={draft} person={p} beforeSend={saveEdit} />
      {limitHit === null && regenerate.error && (
        <p role="alert" className="text-small text-danger">
          {regenerate.error instanceof ApiError
            ? regenerate.error.message
            : copy.common.genericError}
        </p>
      )}
    </div>
  );
}

export default function DraftPage() {
  const { id } = useParams<{ id: string }>();
  const draft = useDraft(id);
  if (!draft.data) {
    return (
      <p role="status" className="px-screen-x pt-6 text-small text-muted">
        {draft.isPending ? `${copy.common.loading}…` : copy.common.genericError}
      </p>
    );
  }
  return <DraftView draft={draft.data} />;
}
