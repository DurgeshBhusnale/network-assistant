"use client";

import { useRouter } from "next/navigation";
import { useSyncExternalStore } from "react";

import { RequireAuth } from "@/components/shell/Gates";
import { Button } from "@/components/ui/Button";
import { copy } from "@/lib/copy/en";

const t = copy.upgrade;

function readReason(): string {
  return new URLSearchParams(window.location.search).get("reason") ?? "free";
}

/** Paywall per Upgrade.dc.html. Static until Razorpay checkout lands (Sprint 7). */
function UpgradeView() {
  const router = useRouter();
  const reason = useSyncExternalStore(
    () => () => {},
    readReason,
    () => "free",
  );

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col gap-4 px-screen-x pt-4 pb-8">
      <button
        type="button"
        aria-label={t.close}
        onClick={() => router.back()}
        className="inline-flex size-tap items-center justify-center self-end rounded-pill border border-line bg-surface text-[18px]"
      >
        ×
      </button>
      <h1 className="m-0 font-display text-h1 font-bold tracking-[-0.01em]">{t.title}</h1>
      <p className="text-body text-ink-2">{reason === "regen" ? t.reasonRegen : t.reasonFree}</p>

      <section className="flex flex-col gap-2 rounded-panel border-2 border-primary bg-surface p-4">
        <span className="self-start rounded-pill bg-accent px-2 py-[3px] text-caption font-semibold text-on-accent">
          {t.badge}
        </span>
        <h2 className="m-0 font-display text-h2 font-semibold">{t.sprintName}</h2>
        <p className="m-0">
          <span className="font-display text-[28px] font-bold">{t.sprintPrice}</span>
          <span className="text-body text-muted">{t.sprintPer}</span>
        </p>
        <span className="text-small text-muted">{t.sprintTerm}</span>
        <ul className="m-0 flex flex-col gap-1 pl-5 text-small text-ink-2">
          {t.sprintBenefits.map((b) => (
            <li key={b}>{b}</li>
          ))}
        </ul>
      </section>

      <section className="flex flex-col gap-1 rounded-panel border border-line bg-surface p-4">
        <h2 className="m-0 font-display text-h2 font-semibold">{t.proName}</h2>
        <p className="m-0">
          <span className="font-display text-[22px] font-bold">{t.proPrice}</span>
          <span className="text-body text-muted">{t.proPer}</span>
        </p>
        <span className="text-small text-ink-2">{t.proBody}</span>
      </section>

      <Button size="lg" fullWidth disabled>
        {t.payUpi}
      </Button>
      <Button variant="secondary" fullWidth disabled>
        {t.payCard}
      </Button>
      <p className="text-small text-muted">{t.paymentsSoon}</p>
      <p className="text-caption text-muted">{t.gst}</p>
    </main>
  );
}

export default function UpgradePage() {
  return (
    <RequireAuth>
      <UpgradeView />
    </RequireAuth>
  );
}
