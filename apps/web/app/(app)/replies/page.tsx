"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { PageHeader } from "@/components/shell/PageHeader";
import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ApiError } from "@/lib/api/client";
import { useCreateDraft } from "@/lib/api/hooks/drafts";
import {
  useLogInteraction,
  useRepliesPending,
  type PendingReply,
  type Replies,
} from "@/lib/api/hooks/loop";
import { usePacks, useActiveGoal } from "@/lib/api/hooks/account";
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
    <Card className="border-accent">
      <span className="text-body font-semibold">
        {t.outcomeTitle(logged.name, logged.outcomeLabel)}
      </span>
      <p className="text-small text-ink-2">{t.thankBody}</p>
      <Button variant="accent" loading={create.isPending} onClick={() => void draftThanks()}>
        {t.draftThanks}
      </Button>
    </Card>
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
  const primaryOutcome = outcomes[0];

  async function mark(type: "replied" | "no_reply" | "outcome", outcomeId?: string) {
    await log.mutateAsync({ contact_id: c.id, type, outcome: outcomeId ?? null });
    if (type === "outcome" && outcomeId) {
      const label = outcomes.find((o) => o.id === outcomeId)?.label ?? outcomeId;
      onOutcome({ contactId: c.id, name: c.full_name, outcomeLabel: label });
    }
  }

  return (
    <Card>
      <div className="flex items-center gap-2.5">
        <Avatar name={c.full_name} />
        <span className="flex min-w-0 flex-col">
          <span className="truncate text-body font-semibold">{c.full_name}</span>
          <span className="truncate text-small text-muted">
            {t.meta(item.stage_label ?? null, c.company ?? null, item.days_ago)}
          </span>
        </span>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" disabled={log.isPending} onClick={() => void mark("replied")}>
          {t.replied}
        </Button>
        <Button variant="secondary" disabled={log.isPending} onClick={() => void mark("no_reply")}>
          {t.notYet}
        </Button>
        {item.stage_has_ask && primaryOutcome ? (
          outcomes.map((o) => (
            <Button
              key={o.id}
              variant={o.id === primaryOutcome.id ? "accent" : "secondary"}
              disabled={log.isPending}
              onClick={() => void mark("outcome", o.id)}
            >
              {o.label}
            </Button>
          ))
        ) : (
          <Button variant="ghost" disabled={log.isPending} onClick={() => void mark("no_reply")}>
            {t.snooze}
          </Button>
        )}
      </div>
      {log.error && (
        <p role="alert" className="text-small text-danger">
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

  return (
    <>
      <PageHeader title={t.title} />
      <div className="flex flex-col gap-gap-cards px-screen-x pt-2">
        {items.length > 0 && <p className="text-body text-ink-2">{t.intro(items.length)}</p>}
        {logged.map((l) => (
          <ThankCard key={l.contactId} logged={l} thankStage={thankStage} />
        ))}
        {replies.isPending && (
          <p role="status" className="text-small text-muted">
            {copy.common.loading}…
          </p>
        )}
        {replies.data && items.length === 0 && logged.length === 0 && (
          <EmptyState title={t.title} body={t.empty} />
        )}
        {items.map((item) => (
          <ReplyCard
            key={item.contact.id}
            item={item}
            outcomes={replies.data?.outcomes ?? []}
            onOutcome={(l) => setLogged((all) => [l, ...all])}
          />
        ))}
        <div className="flex flex-col gap-1 rounded-card border border-dashed border-line-strong p-card">
          <span className="text-small font-semibold">{t.whyTitle}</span>
          <span className="text-small text-muted">{t.whyBody}</span>
        </div>
      </div>
    </>
  );
}
