"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ChatIcon } from "@/components/ui/icons";
import { SectionLabel } from "@/components/ui/SectionLabel";
import { ApiError } from "@/lib/api/client";
import { usePacks, useActiveGoal } from "@/lib/api/hooks/account";
import { useCreateDraft } from "@/lib/api/hooks/drafts";
import {
  useLogInteraction,
  useRepliesPending,
  type PendingReply,
  type Replies,
} from "@/lib/api/hooks/loop";
import { copy } from "@/lib/copy/en";

const t = copy.replies;

type Logged = { contactId: string; name: string; outcomeLabel: string };

function ThankCard({ logged, thankStage }: { logged: Logged; thankStage: string | null }) {
  const create = useCreateDraft(logged.contactId);
  const router = useRouter();
  async function draftThanks() {
    if (!thankStage) return;
    try {
      const d = await create.mutateAsync({ stage: thankStage });
      router.push(`/drafts/${d.id}`);
    } catch (e) {
      if (e instanceof ApiError && e.status === 402) router.push("/upgrade?reason=free");
    }
  }
  return (
    <section className="flex flex-col gap-4 rounded-card bg-info p-card lg:flex-row lg:items-center lg:gap-5 lg:rounded-panel lg:p-7">
      <div className="flex items-center gap-3.5 lg:flex-1 lg:gap-5">
        <Avatar name={logged.name} size="xl" />
        <div className="flex min-w-0 flex-col">
          <SectionLabel as="span" tone="info">
            {logged.outcomeLabel}
          </SectionLabel>
          <span className="text-[16px] leading-[22px] font-semibold lg:text-[20px] lg:leading-7 lg:tracking-[-0.01em]">
            {logged.name}
          </span>
          <p className="m-0 mt-1 hidden text-small text-ink-2 lg:block">{t.thankBody}</p>
        </div>
      </div>
      <p className="m-0 text-small text-ink-2 lg:hidden">{t.thankBody}</p>
      <Button
        className="lg:h-[52px] lg:px-7 lg:shadow-cta"
        loading={create.isPending}
        onClick={() => void draftThanks()}
      >
        {t.draftThanks}
      </Button>
    </section>
  );
}

function ReplyCard({
  item,
  outcomes,
  onOutcome,
}: {
  item: PendingReply;
  outcomes: Replies["outcomes"];
  onOutcome: (logged: Logged) => void;
}) {
  const log = useLogInteraction();
  const c = item.contact;
  const [primary, ...more] = item.stage_has_ask ? outcomes : [];

  async function mark(type: "replied" | "no_reply" | "outcome", outcomeId?: string) {
    await log.mutateAsync({ contact_id: c.id, type, outcome: outcomeId ?? null });
    if (type === "outcome" && outcomeId) {
      const label = outcomes.find((o) => o.id === outcomeId)?.label ?? outcomeId;
      onOutcome({ contactId: c.id, name: c.full_name, outcomeLabel: label });
    }
  }

  return (
    <Card>
      <div className="flex items-center gap-3.5">
        <Avatar name={c.full_name} />
        <span className="flex min-w-0 flex-col">
          <span className="truncate text-lead leading-[22px] font-semibold">{c.full_name}</span>
          <span className="truncate text-small leading-5 text-muted">
            {t.meta(c.company ?? null, item.days_ago)}
          </span>
        </span>
      </div>
      <div className="flex gap-2">
        <Button
          variant="secondary"
          className="flex-1 px-2 text-small"
          disabled={log.isPending}
          onClick={() => void mark("replied")}
        >
          {t.replied}
        </Button>
        <Button
          variant="secondary"
          className="flex-1 px-2 text-small"
          disabled={log.isPending}
          onClick={() => void mark("no_reply")}
        >
          {t.notYet}
        </Button>
        {primary && (
          <Button
            variant="tonal"
            className="flex-[1.2] px-2 text-small"
            disabled={log.isPending}
            onClick={() => void mark("outcome", primary.id)}
          >
            {primary.label}
          </Button>
        )}
      </div>
      {more.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {more.map((o) => (
            <Button
              key={o.id}
              variant="ghost"
              className="min-h-tap text-small"
              disabled={log.isPending}
              onClick={() => void mark("outcome", o.id)}
            >
              {o.label}
            </Button>
          ))}
        </div>
      )}
      {log.error && (
        <p role="alert" className="m-0 text-small text-danger">
          {log.error instanceof ApiError ? log.error.message : copy.common.genericError}
        </p>
      )}
    </Card>
  );
}

export default function RepliesPage() {
  const replies = useRepliesPending();
  const goal = useActiveGoal();
  const packs = usePacks();
  const [logged, setLogged] = useState<Logged[]>([]);
  const pack = packs.data?.find((p) => p.id === goal.data?.pack_id);
  const thankStage =
    (pack?.stages as Array<{ id: string; role?: string }> | undefined)?.find(
      (s) => s.role === "thank",
    )?.id ?? null;
  const items = replies.data?.items ?? [];
  const empty = replies.data && items.length === 0 && logged.length === 0;

  return (
    <div className="flex flex-1 flex-col gap-5 px-screen-x pt-6 lg:gap-8 lg:pt-10">
      <header>
        <h1 className="m-0 title-lg">{t.title}</h1>
        {!empty && (
          <p className="m-0 mt-2 max-w-[560px] text-body leading-[23px] text-muted lg:text-[16px] lg:leading-6">
            {t.intro}
          </p>
        )}
      </header>
      {logged.map((l) => (
        <ThankCard key={l.contactId} logged={l} thankStage={thankStage} />
      ))}
      {replies.isPending && (
        <p role="status" className="text-small text-muted">
          {copy.common.loading}…
        </p>
      )}
      {empty && <EmptyState Icon={ChatIcon} title={t.emptyTitle} body={t.empty} />}
      {items.length > 0 && (
        <div className="flex flex-col gap-5 lg:grid lg:grid-cols-2">
          {items.map((item) => (
            <ReplyCard
              key={item.contact.id}
              item={item}
              outcomes={replies.data?.outcomes ?? []}
              onOutcome={(l) => setLogged((all) => [l, ...all])}
            />
          ))}
        </div>
      )}
      {!empty && (
        <p className="m-0 flex items-start gap-2 text-caption leading-[18px] text-muted">
          {t.whyBody}
        </p>
      )}
    </div>
  );
}
