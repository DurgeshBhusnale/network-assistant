"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useSyncExternalStore } from "react";

import { RequireAuth } from "@/components/shell/Gates";
import { Button } from "@/components/ui/Button";
import { ApiError } from "@/lib/api/client";
import { useMe } from "@/lib/api/hooks/account";
import {
  rupees,
  useCheckoutResult,
  useCreateOrder,
  useDevComplete,
  usePlans,
  useRefreshPlan,
  waitForPaid,
  type Order,
} from "@/lib/api/hooks/billing";
import { copy } from "@/lib/copy/en";
import { openCheckout } from "@/lib/device/razorpay";

const t = copy.upgrade;

function readReason(): string {
  return new URLSearchParams(window.location.search).get("reason") ?? "free";
}

type Phase =
  | { kind: "idle" }
  | { kind: "dev"; order: Order }
  | { kind: "processing" }
  | { kind: "still_processing" }
  | { kind: "done"; days: number }
  | { kind: "cancelled" };

/** Paywall per Upgrade.dc.html (FR-PAY-3/4). The plan unlocks only after the verified webhook. */
function UpgradeView() {
  const router = useRouter();
  const reason = useSyncExternalStore(
    () => () => {},
    readReason,
    () => "free",
  );
  const plans = usePlans();
  const me = useMe();
  const createOrder = useCreateOrder();
  const checkoutResult = useCheckoutResult();
  const devComplete = useDevComplete();
  const refreshPlan = useRefreshPlan();
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });
  const [error, setError] = useState<string | null>(null);

  const sprint = plans.data?.products.find((p) => p.product === "sprint");
  const pro = plans.data?.products.find((p) => p.product === "pro_monthly");
  const proYear = plans.data?.products.find((p) => p.product === "pro_yearly");
  const sprintPrice = sprint ? rupees(sprint.price_paise) : "";

  async function finish(orderId: string) {
    setPhase({ kind: "processing" });
    const status = await waitForPaid(orderId);
    if (status?.status === "paid") {
      await refreshPlan();
      setPhase({ kind: "done", days: status.entitlement.days_left ?? 0 });
    } else {
      setPhase({ kind: "still_processing" });
    }
  }

  async function pay(method: "upi" | "card") {
    setError(null);
    try {
      const order = await createOrder.mutateAsync("sprint");
      if (order.dev_checkout) {
        setPhase({ kind: "dev", order });
        return;
      }
      if (!order.key_id) throw new Error("missing key");
      const result = await openCheckout({
        keyId: order.key_id,
        orderId: order.order_id,
        amountPaise: order.amount_paise,
        name: copy.appName,
        description: t.sprintName,
        email: me.data?.email,
        method,
      });
      if (!result) {
        setPhase({ kind: "cancelled" });
        return;
      }
      await checkoutResult.mutateAsync(result);
      await finish(order.order_id);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : copy.common.genericError);
    }
  }

  async function simulate(order: Order) {
    try {
      await devComplete.mutateAsync(order.order_id);
      await finish(order.order_id);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : copy.common.genericError);
    }
  }

  if (phase.kind === "done") {
    return (
      <main className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col justify-center gap-4 px-screen-x">
        <h1 className="m-0 font-display text-h1 font-bold" role="status">
          {t.success(phase.days)}
        </h1>
        <Link
          href="/today"
          className="inline-flex min-h-cta items-center justify-center rounded-button-lg bg-primary px-5 font-semibold text-on-primary no-underline"
        >
          {t.successAction}
        </Link>
      </main>
    );
  }

  const busy = createOrder.isPending || checkoutResult.isPending || phase.kind === "processing";
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
          <span className="font-display text-[28px] font-bold">{sprintPrice}</span>
          <span className="text-body text-muted">{t.sprintPer}</span>
        </p>
        <span className="text-small text-muted">{t.sprintTerm}</span>
        <ul className="m-0 flex flex-col gap-1 pl-5 text-small text-ink-2">
          {t.sprintBenefits.map((b) => (
            <li key={b}>{b}</li>
          ))}
        </ul>
      </section>

      {pro && (
        <section className="flex flex-col gap-1 rounded-panel border border-line bg-surface p-4">
          <h2 className="m-0 font-display text-h2 font-semibold">{t.proName}</h2>
          <p className="m-0">
            <span className="font-display text-[22px] font-bold">{rupees(pro.price_paise)}</span>
            <span className="text-body text-muted">{t.proPer}</span>
          </p>
          <span className="text-small text-ink-2">
            {t.proBody.replace("₹2,499", proYear ? rupees(proYear.price_paise) : "₹2,499")}
          </span>
          {!pro.enabled && <span className="text-caption text-muted">{t.proSoon}</span>}
        </section>
      )}

      {phase.kind === "dev" ? (
        <div className="flex flex-col gap-2 rounded-card border border-dashed border-line-strong p-card">
          <span className="text-small font-semibold">{t.devTitle}</span>
          <span className="text-small text-muted">{t.devBody}</span>
          <Button loading={devComplete.isPending} onClick={() => void simulate(phase.order)}>
            {t.devConfirm}
          </Button>
        </div>
      ) : (
        <>
          <Button
            size="lg"
            fullWidth
            loading={busy}
            disabled={!sprint}
            onClick={() => void pay("upi")}
          >
            {t.payUpi(sprintPrice)}
          </Button>
          <Button
            variant="secondary"
            fullWidth
            disabled={busy || !sprint}
            onClick={() => void pay("card")}
          >
            {t.payCard}
          </Button>
        </>
      )}
      {(phase.kind === "processing" ||
        phase.kind === "still_processing" ||
        phase.kind === "cancelled") && (
        <p role="status" aria-live="polite" className="text-small text-ink-2">
          {phase.kind === "processing"
            ? t.processing
            : phase.kind === "cancelled"
              ? t.cancelled
              : t.processingStill}
        </p>
      )}
      {error && (
        <p role="alert" className="text-small text-danger">
          {error}
        </p>
      )}
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
