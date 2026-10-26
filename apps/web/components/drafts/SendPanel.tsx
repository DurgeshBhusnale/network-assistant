"use client";

import { useEffect, useState } from "react";

import { BottomBar } from "@/components/ui/BottomBar";
import { Button } from "@/components/ui/Button";
import { ApiError } from "@/lib/api/client";
import type { Draft } from "@/lib/api/hooks/drafts";
import { useLogInteraction, useSend } from "@/lib/api/hooks/loop";
import type { Person } from "@/lib/api/hooks/people";
import { copy } from "@/lib/copy/en";

const t = copy.send;
type Channel = "whatsapp" | "linkedin";

/**
 * The user sends from their own app (ADR-0004): we open WhatsApp/LinkedIn with the text and ask
 * "Sent?" when they come back (FR-SEND-1..4). Nothing is recorded until they confirm.
 */
export function SendPanel({
  draft,
  person,
  beforeSend,
}: {
  draft: Draft;
  person: Person | undefined;
  beforeSend: () => Promise<void>;
}) {
  const send = useSend(draft.id);
  const log = useLogInteraction();
  const [pending, setPending] = useState<Channel | "other" | null>(null);
  const [asking, setAsking] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const firstName = person?.first_name ?? person?.full_name.split(" ")[0] ?? "";

  // Ask "Sent?" when the user returns from WhatsApp/LinkedIn.
  useEffect(() => {
    if (!pending) return;
    function onVisible() {
      if (document.visibilityState === "visible") setAsking(true);
    }
    document.addEventListener("visibilitychange", onVisible);
    return () => document.removeEventListener("visibilitychange", onVisible);
  }, [pending]);

  function failMessage(e: unknown): string {
    return e instanceof ApiError ? e.message : copy.common.genericError;
  }

  async function open(channel: Channel) {
    setNote(null);
    // Open the window during the tap (popup blockers), then point it at the link.
    const win = channel === "whatsapp" || person?.linkedin_url ? window.open("", "_blank") : null;
    try {
      await beforeSend();
      const result = await send.mutateAsync(channel);
      if (channel === "linkedin") {
        await navigator.clipboard.writeText(result.copy_text).catch(() => undefined);
        setNote(t.linkedinCopied);
      }
      if (result.open_url) {
        if (win) win.location.href = result.open_url;
        else window.location.assign(result.open_url);
      } else {
        win?.close();
      }
      setPending(channel);
    } catch (e) {
      win?.close();
      setNote(failMessage(e));
    }
  }

  async function confirm(channel: Channel | "other") {
    try {
      await beforeSend();
      await log.mutateAsync({
        contact_id: draft.contact_id,
        type: "sent",
        draft_id: draft.id,
        channel,
      });
      setAsking(false);
      setPending(null);
      setNote(t.sentDone);
    } catch (e) {
      setNote(failMessage(e));
    }
  }

  if (draft.sent_at) {
    return (
      <BottomBar>
        <p role="status" className="m-0 text-center text-body font-semibold text-success">
          {t.sentDone}
        </p>
      </BottomBar>
    );
  }

  const hasPhone = (person?.phones.length ?? 0) > 0;
  return (
    <BottomBar>
      {asking && pending && (
        <div
          role="dialog"
          aria-label={t.sentQuestion(firstName)}
          className="flex flex-col gap-3 rounded-card bg-tint p-4"
        >
          <span className="text-body font-semibold">{t.sentQuestion(firstName)}</span>
          <div className="flex gap-2.5">
            <Button
              className="flex-1"
              loading={log.isPending}
              onClick={() => void confirm(pending)}
            >
              {t.yesSent}
            </Button>
            <Button variant="secondary" className="flex-1" onClick={() => setAsking(false)}>
              {t.notYet}
            </Button>
          </div>
        </div>
      )}
      <Button
        size="lg"
        fullWidth
        disabled={!hasPhone}
        loading={send.isPending && send.variables === "whatsapp"}
        onClick={() => void open("whatsapp")}
      >
        {t.whatsapp}
      </Button>
      <div className="flex gap-3">
        <Button
          variant="secondary"
          className="flex-1 px-3"
          loading={send.isPending && send.variables === "linkedin"}
          onClick={() => void open("linkedin")}
        >
          {t.linkedin}
        </Button>
        <Button
          variant="secondary"
          className="flex-1 px-3"
          loading={log.isPending && !asking}
          onClick={() => void confirm(pending ?? "other")}
        >
          {t.markSent}
        </Button>
      </div>
      {!hasPhone && <p className="m-0 text-center text-caption text-ink-2">{t.noPhone}</p>}
      <p className="m-0 text-center text-caption leading-[18px] text-muted">{t.trust}</p>
      {note && (
        <p role="status" className="m-0 text-center text-small text-ink-2">
          {note}
        </p>
      )}
    </BottomBar>
  );
}
