"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { StagePicker } from "@/components/drafts/StagePicker";
import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { cn } from "@/components/ui/cn";
import { MicIcon } from "@/components/ui/icons";
import { Sheet } from "@/components/ui/Sheet";
import { ApiError } from "@/lib/api/client";
import {
  useAddMemory,
  useDeleteContact,
  useDeleteMemory,
  usePerson,
  type HistoryItem,
  type Person,
} from "@/lib/api/hooks/people";
import { copy } from "@/lib/copy/en";

const t = copy.person;
const dateFmt = new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short" });

function historyLabel(item: HistoryItem): string {
  switch (item.kind) {
    case "added":
      return t.history.added((item.sources ?? []).map((s) => t.sources[s]).join(", ") || "import");
    case "sent":
      return t.history.sent(item.channel ?? null);
    case "outcome":
      return t.history.outcome(item.outcome ?? null);
    case "met":
    case "replied":
    case "no_reply":
    case "note":
      return t.history[item.kind];
    default:
      return item.kind;
  }
}

function ActionTile({
  label,
  onClick,
  disabled,
  hint,
  children,
}: {
  label: string;
  onClick?: () => void;
  disabled?: boolean;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={hint}
      className={cn(
        "flex min-h-[72px] flex-col items-center justify-center gap-1 rounded-card border border-line bg-surface px-2 text-small font-semibold",
        disabled ? "cursor-not-allowed text-muted" : "text-primary",
      )}
    >
      {children}
      {label}
      {hint && <span className="sr-only">{hint}</span>}
    </button>
  );
}

function PersonView({ person }: { person: Person }) {
  const router = useRouter();
  const addMemory = useAddMemory(person.id);
  const deleteMemory = useDeleteMemory(person.id);
  const deleteContact = useDeleteContact();
  const [noteOpen, setNoteOpen] = useState(false);
  const [note, setNote] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const [stageOpen, setStageOpen] = useState(false);
  const meta = [person.title, person.company, person.city].filter(Boolean).join(" · ");

  async function saveNote() {
    if (!note.trim()) return;
    await addMemory.mutateAsync(note.trim());
    setNote("");
    setNoteOpen(false);
  }

  async function remove() {
    if (!window.confirm(t.deleteConfirm(person.full_name))) return;
    await deleteContact.mutateAsync(person.id);
    router.replace("/people");
  }

  return (
    <div className="flex flex-col gap-gap-cards px-screen-x pt-4">
      <div className="flex items-center justify-between">
        <button
          type="button"
          aria-label={t.back}
          onClick={() => router.back()}
          className="inline-flex size-tap items-center justify-center rounded-pill border border-line bg-surface"
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
        <div className="relative">
          <button
            type="button"
            aria-label={t.moreOptions}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((o) => !o)}
            className="inline-flex size-tap items-center justify-center rounded-pill border border-line bg-surface"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <circle cx="5" cy="12" r="2" />
              <circle cx="12" cy="12" r="2" />
              <circle cx="19" cy="12" r="2" />
            </svg>
          </button>
          {menuOpen && (
            <div className="absolute right-0 z-10 mt-1 flex w-48 flex-col rounded-card border border-line bg-surface p-1 shadow-fab">
              <Link
                href={`/people/${person.id}/edit`}
                className="flex min-h-tap items-center rounded-button px-3 text-body text-ink no-underline"
              >
                {t.edit}
              </Link>
              <button
                type="button"
                onClick={remove}
                className="flex min-h-tap items-center rounded-button px-3 text-left text-body text-danger"
              >
                {t.delete}
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="flex flex-col items-center gap-1 text-center">
        <Avatar name={person.full_name} size="lg" />
        <h1 className="m-0 mt-2 font-display text-[24px] font-bold">{person.full_name}</h1>
        {meta && <p className="text-small text-ink-2">{meta}</p>}
        {person.how_known && <p className="text-small text-muted">{person.how_known}</p>}
      </div>

      <div className="grid grid-cols-3 gap-2">
        <ActionTile label={t.draft} onClick={() => setStageOpen(true)}>
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
            <path d="M4 20h4L19 9l-4-4L4 16v4z" />
          </svg>
        </ActionTile>
        <ActionTile label={t.addNote} onClick={() => setNoteOpen(true)}>
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
            <path d="M12 5v14M5 12h14" />
          </svg>
        </ActionTile>
        <ActionTile label={t.voiceMemory} disabled hint={t.voiceSoon}>
          <MicIcon size={20} />
        </ActionTile>
      </div>

      {person.next_step && (
        <div className="flex flex-col gap-1 rounded-card bg-accent-soft p-card text-accent-text">
          <span className="text-caption font-semibold tracking-[0.06em] uppercase">
            {t.nextStep}
          </span>
          <span className="text-body font-semibold">
            {person.next_step.stage_label ?? t.nextStepPending}
          </span>
          <span className="text-small">{person.next_step.goal_label}</span>
        </div>
      )}

      <Card>
        <h2 className="m-0 font-display text-h2 font-semibold">{t.rememberTitle}</h2>
        {person.memories.length === 0 ? (
          <p className="text-small text-muted">{t.rememberEmpty}</p>
        ) : (
          <ul className="m-0 flex list-none flex-col gap-3 p-0">
            {person.memories.map((m) => (
              <li key={m.id} className="flex items-start justify-between gap-2">
                <span className="flex flex-col">
                  <span className="text-body">{m.text}</span>
                  <span className="text-caption text-muted">
                    {t.memorySource[m.source]} · {dateFmt.format(new Date(m.created_at))}
                  </span>
                </span>
                <button
                  type="button"
                  aria-label={t.deleteNote}
                  onClick={() => deleteMemory.mutate(m.id)}
                  className="inline-flex size-tap shrink-0 items-center justify-center text-muted"
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card>
        <h2 className="m-0 font-display text-h2 font-semibold">{t.historyTitle}</h2>
        <ol className="m-0 flex list-none flex-col gap-3 p-0">
          {person.history.map((h, i) => (
            <li key={`${h.kind}-${h.occurred_at}-${i}`} className="flex items-center gap-2.5">
              <span
                aria-hidden="true"
                className={cn(
                  "size-2 shrink-0 rounded-pill",
                  h.kind === "replied" || h.kind === "outcome"
                    ? "bg-success"
                    : h.kind === "sent"
                      ? "bg-primary"
                      : "bg-dot-neutral",
                )}
              />
              <span className="flex-1 text-body">{historyLabel(h)}</span>
              <span className="text-caption text-muted">
                {dateFmt.format(new Date(h.occurred_at))}
              </span>
            </li>
          ))}
        </ol>
      </Card>

      <StagePicker contactId={person.id} open={stageOpen} onClose={() => setStageOpen(false)} />

      <Sheet open={noteOpen} title={t.addNote} onClose={() => setNoteOpen(false)}>
        <label htmlFor="note-text" className="text-small font-semibold">
          {t.noteLabel}
        </label>
        <textarea
          id="note-text"
          rows={4}
          maxLength={2000}
          value={note}
          placeholder={t.notePlaceholder}
          onChange={(e) => setNote(e.target.value)}
          className="rounded-button border border-line-strong bg-surface p-3 text-body"
        />
        {addMemory.error && (
          <p role="alert" className="text-small text-danger">
            {addMemory.error instanceof ApiError
              ? addMemory.error.message
              : copy.common.genericError}
          </p>
        )}
        <Button
          size="lg"
          fullWidth
          loading={addMemory.isPending}
          disabled={!note.trim()}
          onClick={saveNote}
        >
          {t.saveNote}
        </Button>
      </Sheet>
    </div>
  );
}

export default function PersonPage() {
  const { id } = useParams<{ id: string }>();
  const person = usePerson(id);

  if (person.isPending) {
    return (
      <p role="status" className="px-screen-x pt-6 text-small text-muted">
        {copy.common.loading}…
      </p>
    );
  }
  if (!person.data) {
    return (
      <div className="flex flex-col gap-2 px-screen-x pt-6">
        <p className="text-body">{t.notFound}</p>
        <Link href="/people" className="font-semibold">
          {copy.people.title}
        </Link>
      </div>
    );
  }
  return <PersonView person={person.data} />;
}
