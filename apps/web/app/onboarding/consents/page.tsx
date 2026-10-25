"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { CheckboxRow } from "@/components/ui/CheckboxRow";
import { FullScreenLoader } from "@/components/ui/FullScreenLoader";
import { ApiError } from "@/lib/api/client";
import { useConsents, useUpdateConsents, type Consents } from "@/lib/api/hooks/account";
import { copy } from "@/lib/copy/en";

type Kind = "contacts" | "voice" | "whatsapp" | "analytics";
const KINDS: Kind[] = ["contacts", "voice", "whatsapp", "analytics"];

export default function ConsentsPage() {
  const consents = useConsents();
  if (consents.isPending) return <FullScreenLoader />;
  return <ConsentsForm initial={consents.data} />;
}

function initialChoices(initial: Consents | undefined): Record<Kind, boolean> {
  // DPDP: consent is an active opt-in, so nothing is pre-ticked.
  if (!initial?.notice_accepted) {
    return { contacts: false, voice: false, whatsapp: false, analytics: false };
  }
  const c = initial.consents;
  return {
    contacts: c.contacts?.granted ?? false,
    voice: c.voice?.granted ?? false,
    whatsapp: c.whatsapp?.granted ?? false,
    analytics: c.analytics?.granted ?? false,
  };
}

function ConsentsForm({ initial }: { initial: Consents | undefined }) {
  const update = useUpdateConsents();
  const router = useRouter();
  const t = copy.consents;
  const [accepted, setAccepted] = useState(initial?.notice_accepted ?? false);
  const [choices, setChoices] = useState(() => initialChoices(initial));
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!accepted) {
      setError(t.mustAccept);
      return;
    }
    setError(null);
    try {
      await update.mutateAsync({ accept_notice: true, consents: choices });
      router.replace("/onboarding/goal");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : copy.common.genericError);
    }
  }

  return (
    <>
      <h1 className="m-0 font-display text-h1 font-bold tracking-[-0.01em]">{t.title}</h1>
      <p className="text-body text-ink-2">{t.intro}</p>

      <section
        aria-label="Privacy notice"
        className="flex max-h-[320px] flex-col gap-3 overflow-y-auto rounded-card border border-line bg-surface p-card"
      >
        {t.noticeSections.map((s) => (
          <div key={s.heading} className="flex flex-col gap-1">
            <h2 className="m-0 text-small font-semibold">{s.heading}</h2>
            <p className="text-small text-ink-2">{s.body}</p>
          </div>
        ))}
        <p className="text-caption text-muted">{t.reviewNote}</p>
      </section>

      <CheckboxRow label={t.acceptNotice} checked={accepted} onChange={setAccepted} />

      <h2 className="m-0 font-display text-h2 font-semibold">{t.choicesTitle}</h2>
      <div className="flex flex-col gap-gap-cards">
        {KINDS.map((kind) => (
          <CheckboxRow
            key={kind}
            label={t.items[kind].label}
            detail={t.items[kind].detail}
            checked={choices[kind]}
            onChange={(checked) => setChoices((c) => ({ ...c, [kind]: checked }))}
          />
        ))}
      </div>

      {error && (
        <p role="alert" className="text-small text-danger">
          {error}
        </p>
      )}
      <Button size="lg" fullWidth loading={update.isPending} onClick={submit}>
        {copy.common.continue}
      </Button>
    </>
  );
}
