"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { StagePicker } from "@/components/drafts/StagePicker";
import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { cn } from "@/components/ui/cn";
import { IconButton } from "@/components/ui/IconButton";
import { BackIcon, ChatIcon, CloseIcon, EditIcon, MicIcon, MoreIcon } from "@/components/ui/icons";
import { SectionLabel } from "@/components/ui/SectionLabel";
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
const dateFmt = new Intl.DateTimeFormat("en-IN", {
  day: "numeric",
  month: "short",
  year: "numeric",
});

function historyLabel(item: HistoryItem): string {
  switch (item.kind) {
    case "added":
      return t.history.added(
        (item.sources ?? []).map((s) => t.sources[s]).join(", ") || "from an import",
      );
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

const DOT: Record<string, string> = {
  replied: "bg-grad-to",
  outcome: "bg-grad-to",
  sent: "bg-grad-from",
  met: "bg-grad-from",
};

function QuickAction({
  label,
  onClick,
  primary = false,
  children,
}: {
  label: string;
  onClick: () => void;
  primary?: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-24 flex-col items-center gap-2.5 bg-transparent text-caption font-semibold text-ink lg:h-[72px] lg:w-auto lg:flex-row lg:gap-3.5 lg:rounded-tile lg:bg-surface lg:px-[18px] lg:text-[15px] lg:shadow-[0_0_0_1px_var(--color-line)] lg:hover:bg-surface-2"
    >
      <span
        aria-hidden="true"
        className={cn(
          "flex size-14 shrink-0 items-center justify-center rounded-pill lg:size-10 lg:[&>svg]:size-5",
          primary
            ? "bg-grad text-on-primary shadow-cta"
            : "bg-surface text-ink hairline-strong lg:bg-field lg:shadow-none",
        )}
      >
        {children}
      </span>
      {label}
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
    <div className="flex flex-col gap-8 px-screen-x pt-6 lg:pt-10">
      <div className="flex items-center justify-between lg:hidden">
        <IconButton label={t.back} onClick={() => router.back()}>
          <BackIcon />
        </IconButton>
        <div className="relative">
          <IconButton
            label={t.moreOptions}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((o) => !o)}
          >
            <MoreIcon />
          </IconButton>
          {menuOpen && (
            <div className="absolute right-0 z-10 mt-2 flex w-52 flex-col rounded-button bg-surface p-1.5 shadow-panel">
              <Link
                href={`/people/${person.id}/edit`}
                className="flex min-h-tap items-center rounded-[12px] px-3 text-body text-ink no-underline hover:bg-surface-2 hover:text-ink"
              >
                {t.edit}
              </Link>
              <button
                type="button"
                onClick={remove}
                className="flex min-h-tap items-center rounded-[12px] px-3 text-left text-body text-danger hover:bg-danger-soft"
              >
                {t.delete}
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="-mt-2 flex flex-col items-center text-center lg:mt-0 lg:flex-row lg:gap-6 lg:text-left">
        <span className="hidden lg:block">
          <IconButton label={t.back} onClick={() => router.back()}>
            <BackIcon />
          </IconButton>
        </span>
        <Avatar name={person.full_name} size="hero" />
        <div className="flex flex-col items-center lg:flex-1 lg:items-start">
          <h1 className="m-0 mt-5 title lg:mt-0">{person.full_name}</h1>
          {meta && (
            <p className="m-0 mt-1 text-body leading-[22px] text-muted lg:text-[16px]">{meta}</p>
          )}
        </div>
        {person.how_known && (
          <span className="mt-4 inline-flex min-h-8 items-center rounded-pill bg-surface px-3.5 text-caption text-ink-2 hairline lg:mt-0 lg:min-h-9 lg:px-4 lg:text-small">
            {person.how_known}
          </span>
        )}
        <div className="relative hidden lg:block">
          <IconButton
            label={t.moreOptions}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((o) => !o)}
          >
            <MoreIcon />
          </IconButton>
          {menuOpen && (
            <div className="absolute right-0 z-10 mt-2 flex w-52 flex-col rounded-button bg-surface p-1.5 shadow-panel">
              <Link
                href={`/people/${person.id}/edit`}
                className="flex min-h-tap items-center rounded-[12px] px-3 text-body text-ink no-underline hover:bg-surface-2 hover:text-ink"
              >
                {t.edit}
              </Link>
              <button
                type="button"
                onClick={remove}
                className="flex min-h-tap items-center rounded-[12px] px-3 text-left text-body text-danger hover:bg-danger-soft"
              >
                {t.delete}
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="flex flex-col gap-8 lg:grid lg:grid-cols-[minmax(0,1fr)_400px] lg:items-start">
        <div className="flex flex-col gap-8 lg:gap-7">
          <div className="flex justify-between px-2 lg:grid lg:grid-cols-3 lg:gap-4 lg:px-0">
            <QuickAction primary label={t.draft} onClick={() => setStageOpen(true)}>
              <ChatIcon size={24} />
            </QuickAction>
            <QuickAction label={t.addNote} onClick={() => setNoteOpen(true)}>
              <EditIcon size={24} />
            </QuickAction>
            <QuickAction
              label={t.voiceMemory}
              onClick={() => router.push(`/capture?contact=${person.id}`)}
            >
              <MicIcon size={24} />
            </QuickAction>
          </div>

          {person.next_step && (
            <section className="flex flex-col gap-2 rounded-card bg-tint p-card lg:p-7">
              <SectionLabel as="span" tone="accent">
                {t.nextStep}
              </SectionLabel>
              <span className="text-[18px] leading-6 font-semibold tracking-[-0.01em]">
                {person.next_step.stage_label ?? t.nextStepPending}
              </span>
              <span className="text-small leading-[21px] text-ink-2">
                {person.next_step.goal_label}
              </span>
            </section>
          )}

          <section className="flex flex-col">
            <SectionLabel className="mb-1">{t.rememberTitle}</SectionLabel>
            {person.memories.length === 0 ? (
              <p className="m-0 py-4 text-body text-muted">{t.rememberEmpty}</p>
            ) : (
              <ul className="m-0 flex list-none flex-col p-0">
                {person.memories.map((m) => (
                  <li
                    key={m.id}
                    className="flex items-start gap-2 border-b border-line py-4 lg:gap-6"
                  >
                    <span className="flex flex-1 flex-col lg:flex-row lg:justify-between lg:gap-6">
                      <span className="text-body leading-[22px]">{m.text}</span>
                      <span className="mt-1 text-caption text-muted lg:mt-0 lg:leading-[22px] lg:whitespace-nowrap">
                        {t.memorySource[m.source]} · {dateFmt.format(new Date(m.created_at))}
                      </span>
                    </span>
                    <button
                      type="button"
                      aria-label={t.deleteNote}
                      onClick={() => deleteMemory.mutate(m.id)}
                      className="-mt-2 -mr-2 inline-flex size-tap shrink-0 items-center justify-center text-muted hover:text-danger"
                    >
                      <CloseIcon size={18} />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>

        <section className="flex flex-col lg:rounded-card lg:bg-surface lg:p-7 lg:shadow-[0_0_0_1px_var(--color-line)]">
          <SectionLabel className="mb-4 lg:mb-5">{t.historyTitle}</SectionLabel>
          <ol className="m-0 flex list-none flex-col p-0">
            {person.history.map((h, i) => (
              <li key={`${h.kind}-${h.occurred_at}-${i}`} className="flex min-h-[60px] gap-4">
                <span aria-hidden="true" className="flex w-3 flex-col items-center">
                  <span
                    className={cn(
                      "mt-[5px] size-2.5 shrink-0 rounded-pill",
                      DOT[h.kind] ?? "bg-line-accent",
                    )}
                  />
                  {i < person.history.length - 1 && (
                    <span className="mt-1 w-[1.5px] flex-1 bg-line-soft" />
                  )}
                </span>
                <span className="flex flex-col pb-4">
                  <span className="text-body leading-[22px] font-semibold">{historyLabel(h)}</span>
                  <span className="text-caption leading-[18px] text-muted">
                    {dateFmt.format(new Date(h.occurred_at))}
                  </span>
                </span>
              </li>
            ))}
          </ol>
        </section>
      </div>

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
          className="rounded-button bg-surface p-4 text-[16px] hairline-strong placeholder:text-muted focus:shadow-[inset_0_0_0_1.5px_var(--color-primary-ring)] focus:outline-none"
        />
        {addMemory.error && (
          <p role="alert" className="m-0 text-small text-danger">
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
        <h1 className="m-0 title">{t.notFound}</h1>
        <Link href="/people" className="font-semibold">
          {copy.people.title}
        </Link>
      </div>
    );
  }
  return <PersonView person={person.data} />;
}
