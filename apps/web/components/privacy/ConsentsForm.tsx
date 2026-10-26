"use client";

import { useState } from "react";

import { LegalLinks } from "@/components/legal/LegalLinks";
import { Button } from "@/components/ui/Button";
import { CheckboxRow } from "@/components/ui/CheckboxRow";
import { ApiError } from "@/lib/api/client";
import { useUpdateConsents, type Consents } from "@/lib/api/hooks/account";
import { copy } from "@/lib/copy/en";

type Kind = "contacts" | "voice" | "whatsapp" | "analytics";
const KINDS: Kind[] = ["contacts", "voice", "whatsapp", "analytics"];

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

/** Itemised notice + opt-in consents (FR-ONB-3, FR-PRIV-1). Used in onboarding and Settings. */
export function ConsentsForm({
  initial,
  onSaved,
  submitLabel = copy.common.continue,
}: {
  initial: Consents | undefined;
  onSaved: () => void;
  submitLabel?: string;
}) {
  const update = useUpdateConsents();
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
      onSaved();
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
        <LegalLinks />
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
        {submitLabel}
      </Button>
    </>
  );
}
