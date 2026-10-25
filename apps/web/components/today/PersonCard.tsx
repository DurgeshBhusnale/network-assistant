"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { IconButton } from "@/components/ui/IconButton";
import { SnoozeIcon } from "@/components/ui/icons";
import { Sheet } from "@/components/ui/Sheet";
import { StageBadge } from "@/components/ui/StageBadge";
import { ApiError } from "@/lib/api/client";
import {
  useDismiss,
  useSnooze,
  useSuggestionDraft,
  type SuggestionItem,
} from "@/lib/api/hooks/loop";
import { copy } from "@/lib/copy/en";

const t = copy.today;

/** Who, why now, what next (FR-TODAY-2). */
export function PersonCard({ item }: { item: SuggestionItem }) {
  const router = useRouter();
  const draft = useSuggestionDraft();
  const snooze = useSnooze();
  const dismiss = useDismiss();
  const [menu, setMenu] = useState(false);
  const c = item.contact;
  const meta = [c.title, c.company, c.how_known].filter(Boolean).join(" · ");
  const sent = item.status === "sent";

  async function open() {
    if (item.draft_id) {
      router.push(`/drafts/${item.draft_id}`);
      return;
    }
    try {
      const d = await draft.mutateAsync(item.id);
      router.push(`/drafts/${d.id}`);
    } catch (e) {
      if (e instanceof ApiError && e.status === 402) {
        router.push(`/upgrade?reason=${e.code === "FREE_REGEN_LIMIT_REACHED" ? "regen" : "free"}`);
      }
    }
  }

  return (
    <Card className={sent ? "opacity-70" : undefined}>
      <div className="flex items-start justify-between gap-2">
        <Link
          href={`/people/${c.id}`}
          className="flex min-w-0 items-center gap-2.5 text-ink no-underline"
        >
          <Avatar name={c.full_name} />
          <span className="flex min-w-0 flex-col">
            <span className="truncate text-body font-semibold">{c.full_name}</span>
            {meta && <span className="truncate text-small text-muted">{meta}</span>}
          </span>
        </Link>
        <StageBadge
          tone={item.stage_tone}
          label={sent ? copy.send.alreadySent : item.stage_label}
        />
      </div>
      {item.reasons.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {item.reasons.map((r) => (
            <Chip key={r.text} tone={r.highlight ? "highlight" : "neutral"}>
              {r.text}
            </Chip>
          ))}
        </div>
      )}
      {!sent && (
        <div className="flex gap-2">
          <Button className="flex-1" loading={draft.isPending} onClick={() => void open()}>
            {draft.isPending ? t.writing : item.draft_id ? t.viewDraft : t.openDraft}
          </Button>
          <IconButton label={t.snooze} onClick={() => setMenu(true)}>
            <SnoozeIcon />
          </IconButton>
        </div>
      )}
      {draft.error instanceof ApiError && draft.error.status !== 402 && (
        <p role="alert" className="text-small text-danger">
          {draft.error.message}
        </p>
      )}
      <Sheet open={menu} title={c.full_name} onClose={() => setMenu(false)}>
        <Button
          variant="secondary"
          fullWidth
          onClick={() => snooze.mutate({ id: item.id, days: 1 })}
        >
          {t.snoozeDay}
        </Button>
        <Button
          variant="secondary"
          fullWidth
          onClick={() => snooze.mutate({ id: item.id, days: 7 })}
        >
          {t.snoozeWeek}
        </Button>
        <Button variant="ghost" fullWidth onClick={() => dismiss.mutate(item.id)}>
          {t.notRelevant}
        </Button>
      </Sheet>
    </Card>
  );
}
