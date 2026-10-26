"use client";

import { useParams, useRouter } from "next/navigation";
import { useRef, useState } from "react";

import { SendPanel } from "@/components/drafts/SendPanel";
import { Avatar } from "@/components/ui/Avatar";
import { cn } from "@/components/ui/cn";
import { IconButton } from "@/components/ui/IconButton";
import { BackIcon, EditIcon, RefreshIcon } from "@/components/ui/icons";
import { SectionLabel } from "@/components/ui/SectionLabel";
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
  const textRef = useRef<HTMLTextAreaElement>(null);
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
  const meta = p ? [p.title, p.company].filter(Boolean).join(" · ") : "";
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
    <div className="flex flex-col gap-6 px-screen-x pt-6 pb-[260px]">
      <div className="flex items-center gap-3.5">
        <IconButton label={t.back} onClick={() => router.back()}>
          <BackIcon />
        </IconButton>
        {p && <Avatar name={p.full_name} size="md" />}
        <div className="flex min-w-0 flex-col">
          <h1 className="m-0 truncate text-[18px] leading-[22px] font-semibold tracking-[-0.01em]">
            {p?.full_name ?? ""}
          </h1>
          {meta && <span className="truncate text-small leading-5 text-muted">{meta}</span>}
        </div>
      </div>

      <section className="flex flex-col gap-3">
        <SectionLabel as="p" tone="accent">
          {t.stepBadge(draft.step, draft.total_steps, draft.stage_label)}
        </SectionLabel>
        <div className="rounded-panel bg-surface px-6 pt-6 shadow-panel">
          <label htmlFor="draft-text" className="sr-only">
            {t.messageLabel}
          </label>
          <textarea
            id="draft-text"
            ref={textRef}
            value={busy ? t.writing : text}
            readOnly={busy}
            aria-busy={busy}
            onChange={(e) => setText(e.target.value)}
            onBlur={() => void saveEdit()}
            rows={8}
            className={cn(
              "block min-h-[140px] w-full resize-none border-0 bg-transparent p-0 text-lead leading-7 tracking-[-0.005em] text-ink [field-sizing:content] focus:outline-none",
              busy && "text-muted",
            )}
          />
          <div className="mt-5 flex h-[52px] items-center justify-between gap-2 border-t border-line">
            <span className="text-caption text-muted" aria-live="polite">
              {edit.isSuccess && !busy ? t.saved : t.meta(wordCount(text))}
            </span>
            <button
              type="button"
              onClick={() => textRef.current?.focus()}
              className="inline-flex min-h-tap items-center gap-1.5 bg-transparent text-small font-semibold text-primary"
            >
              <EditIcon size={16} />
              {t.edit}
            </button>
          </div>
        </div>
      </section>

      <section className="flex flex-col gap-2">
        <div
          className="no-scrollbar -mx-screen-x flex gap-2 overflow-x-auto px-screen-x"
          role="group"
          aria-label={t.toneLabel}
        >
          {TONES.map((tone) => (
            <button
              key={tone}
              type="button"
              disabled={busy}
              aria-pressed={draft.tone === tone}
              onClick={() => void rewrite(tone)}
              className={cn(
                "flex h-11 shrink-0 items-center rounded-pill px-[18px] text-small font-medium whitespace-nowrap disabled:opacity-50",
                draft.tone === tone
                  ? "bg-ink text-on-primary"
                  : "bg-surface text-ink hairline-strong",
              )}
            >
              {t.tones[tone]}
            </button>
          ))}
        </div>
        <div className="flex items-center justify-between gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={() => void rewrite(null)}
            className="inline-flex h-11 items-center gap-2 bg-transparent text-body font-semibold text-primary disabled:opacity-50"
          >
            <RefreshIcon size={18} />
            {t.anotherVersion}
          </button>
          {draft.regenerations_left !== null && (
            <span className="text-caption text-muted">
              {t.rewritesLeft(draft.regenerations_left)}
            </span>
          )}
        </div>
      </section>

      {(draft.warnings.length > 0 || draft.unsupported_claims.length > 0) && (
        <section role="alert" className="flex flex-col gap-2 rounded-card bg-tint p-card">
          <SectionLabel as="span" tone="accent">
            {t.checkTitle}
          </SectionLabel>
          {draft.unsupported_claims.length > 0 && (
            <>
              <span className="text-small text-ink-2">{t.unsupported}</span>
              <ul className="m-0 pl-5 text-small text-ink">
                {draft.unsupported_claims.map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
            </>
          )}
          {draft.warnings
            .filter((w) => w !== "unsupported_claims")
            .map((w) => (
              <span key={w} className="text-small text-ink">
                {t.warnings[w as keyof typeof t.warnings] ?? w}
              </span>
            ))}
        </section>
      )}

      {draft.reasons.length > 0 && (
        <section className="flex flex-col gap-3.5 rounded-card bg-surface-2 p-card hairline">
          <SectionLabel>{t.whyTitle(firstName)}</SectionLabel>
          <ul className="m-0 flex list-none flex-col gap-3.5 p-0">
            {draft.reasons.map((r) => (
              <li key={r} className="flex gap-3 text-body leading-[22px]">
                <span aria-hidden="true" className="mt-2 size-1.5 shrink-0 rounded-pill bg-grad" />
                {r}
              </li>
            ))}
          </ul>
        </section>
      )}

      {limitHit === null && regenerate.error && (
        <p role="alert" className="m-0 text-small text-danger">
          {regenerate.error instanceof ApiError
            ? regenerate.error.message
            : copy.common.genericError}
        </p>
      )}
      <SendPanel draft={draft} person={p} beforeSend={saveEdit} />
    </div>
  );
}

export default function DraftPage() {
  const { id } = useParams<{ id: string }>();
  const draft = useDraft(id);
  if (!draft.data) {
    return (
      <p role="status" className="m-0 px-screen-x pt-6 text-small text-muted">
        {draft.isPending ? `${copy.common.loading}…` : copy.common.genericError}
      </p>
    );
  }
  return <DraftView draft={draft.data} />;
}
