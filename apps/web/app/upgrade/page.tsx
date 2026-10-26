"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useSyncExternalStore } from "react";

import { RequireAuth } from "@/components/shell/Gates";
import { BottomBar } from "@/components/ui/BottomBar";
import { Button, buttonClasses } from "@/components/ui/Button";
import { IconButton } from "@/components/ui/IconButton";
import { CheckIcon, CloseIcon } from "@/components/ui/icons";
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
      <main className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col items-center justify-center gap-5 px-screen-x text-center">
        <span
          aria-hidden="true"
          className="flex size-[72px] items-center justify-center rounded-pill bg-grad text-on-primary shadow-cta"
        >
          <CheckIcon size={32} strokeWidth={2.4} />
        </span>
        <h1 className="m-0 title" role="status">
          {t.success(phase.days)}
        </h1>
        <Link href="/today" className={buttonClasses({ size: "lg", fullWidth: true })}>
          {t.successAction}
        </Link>
      </main>
    );
  }

  const busy = createOrder.isPending || checkoutResult.isPending || phase.kind === "processing";
  const proOn = Boolean(pro?.enabled);
  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col gap-6 px-screen-x pt-6 pb-[260px]">
      <div className="flex justify-end">
        <IconButton label={t.close} onClick={() => router.back()}>
          <CloseIcon size={20} />
        </IconButton>
      </div>
      <div>
        <h1 className="m-0 title-lg">{t.title}</h1>
        <p className="m-0 mt-2.5 text-body leading-[22px] text-muted">
          {reason === "regen" ? t.reasonRegen : t.reasonFree}
        </p>
      </div>

      <section className="rounded-panel bg-grad p-[1.5px] shadow-[0_20px_40px_-20px_rgba(76,79,214,0.5)]">
        <div className="flex flex-col gap-5 rounded-[26.5px] bg-surface p-6">
          <div className="flex items-start justify-between gap-3">
            <div className="flex flex-col">
              <span className="inline-flex h-6 items-center self-start rounded-badge bg-primary-soft px-2.5 text-label font-semibold text-primary">
                {t.badge}
              </span>
              <h2 className="m-0 mt-3 font-display text-[24px] leading-[30px] font-semibold tracking-[-0.02em]">
                {t.sprintName}
              </h2>
              <span className="text-small text-muted">{t.sprintTerm}</span>
            </div>
            <span className="font-display text-[36px] leading-10 font-semibold tracking-[-0.03em]">
              {sprintPrice}
            </span>
          </div>
          <ul className="m-0 flex list-none flex-col gap-3 border-t border-line p-0 pt-5">
            {t.sprintBenefits.map((b) => (
              <li key={b} className="flex items-start gap-3 text-body leading-[22px]">
                <span
                  aria-hidden="true"
                  className="mt-px flex size-5 shrink-0 items-center justify-center rounded-pill bg-primary-soft text-primary"
                >
                  <CheckIcon size={12} strokeWidth={3} />
                </span>
                {b}
              </li>
            ))}
          </ul>
        </div>
      </section>

      {proOn && pro && (
        <section className="flex items-center gap-3 rounded-card bg-surface px-5 py-[18px] hairline">
          <div className="flex flex-1 flex-col">
            <h2 className="m-0 text-[16px] leading-[22px] font-semibold">{t.proName}</h2>
            <span className="text-small leading-5 text-muted">{t.proBody}</span>
          </div>
          <span className="text-[20px] font-semibold">
            {rupees(pro.price_paise)}
            <span className="text-small font-medium text-muted">{t.proPer}</span>
          </span>
        </section>
      )}

      {phase.kind === "dev" && (
        <section className="flex flex-col gap-3 rounded-card bg-tint p-card">
          <span className="label-caps text-primary">{t.devTitle}</span>
          <span className="text-small text-ink-2">{t.devBody}</span>
          <Button loading={devComplete.isPending} onClick={() => void simulate(phase.order)}>
            {t.devConfirm}
          </Button>
        </section>
      )}
      {(phase.kind === "processing" ||
        phase.kind === "still_processing" ||
        phase.kind === "cancelled") && (
        <p role="status" aria-live="polite" className="m-0 text-small text-ink-2">
          {phase.kind === "processing"
            ? t.processing
            : phase.kind === "cancelled"
              ? t.cancelled
              : t.processingStill}
        </p>
      )}
      {error && (
        <p role="alert" className="m-0 text-small text-danger">
          {error}
        </p>
      )}

      {phase.kind !== "dev" && (
        <BottomBar>
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
          <p className="m-0 text-center text-caption text-muted">{t.gst}</p>
        </BottomBar>
      )}
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
