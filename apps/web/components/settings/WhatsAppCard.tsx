"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ApiError } from "@/lib/api/client";
import {
  useLinkCode,
  useRefreshWhatsAppStatus,
  useUnlinkWhatsApp,
  useWhatsAppStatus,
} from "@/lib/api/hooks/whatsapp";
import { copy } from "@/lib/copy/en";

const t = copy.settings;

/** FR-WA-1: link by sending "START <code>" from the user's own WhatsApp; the webhook verifies it. */
export function WhatsAppCard() {
  const status = useWhatsAppStatus();
  const link = useLinkCode();
  const unlink = useUnlinkWhatsApp();
  const refresh = useRefreshWhatsAppStatus();
  const [hint, setHint] = useState<string | null>(null);

  // After the user comes back from WhatsApp, re-check the link status.
  useEffect(() => {
    function onVisible() {
      if (document.visibilityState === "visible") void refresh();
    }
    document.addEventListener("visibilitychange", onVisible);
    return () => document.removeEventListener("visibilitychange", onVisible);
  }, [refresh]);

  async function start() {
    const win = window.open("", "_blank");
    try {
      const code = await link.mutateAsync();
      setHint(t.whatsappCodeHint(code.expires_in_minutes));
      if (win) win.location.href = code.wa_url;
      else window.location.assign(code.wa_url);
    } catch (e) {
      win?.close();
      if (e instanceof ApiError && e.code === "CONSENT_REQUIRED") setHint(t.whatsappConsent);
      else setHint(e instanceof ApiError ? e.message : copy.common.genericError);
    }
  }

  const s = status.data;
  return (
    <Card>
      <h2 className="m-0 font-display text-h2 font-semibold">{t.whatsappTitle}</h2>
      <p className="text-small text-ink-2">{t.whatsappBody}</p>
      {s && !s.number_configured ? (
        <p className="text-small text-muted">{t.whatsappNotSetUp}</p>
      ) : s?.linked ? (
        <>
          <p className="text-small font-semibold text-success">
            {t.whatsappLinked(s.phone_hint ?? "")}
          </p>
          {s.opted_out && <p className="text-small text-muted">{t.whatsappOptedOut}</p>}
          <Button variant="secondary" loading={unlink.isPending} onClick={() => unlink.mutate()}>
            {t.whatsappUnlink}
          </Button>
        </>
      ) : (
        <Button variant="send" loading={link.isPending} onClick={() => void start()}>
          {t.whatsappLink}
        </Button>
      )}
      {hint && (
        <p role="status" className="text-small text-ink-2">
          {hint}
          {hint === t.whatsappConsent && (
            <>
              {" "}
              <Link href="/onboarding/consents" className="font-semibold">
                {copy.importFlow.consentLink}
              </Link>
            </>
          )}
        </p>
      )}
    </Card>
  );
}
