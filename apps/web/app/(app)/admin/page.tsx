"use client";

import { PageHeader } from "@/components/shell/PageHeader";
import { Card } from "@/components/ui/Card";
import { ApiError } from "@/lib/api/client";
import { useAdminMetrics } from "@/lib/api/hooks/account";
import { copy } from "@/lib/copy/en";

const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" });

function Row({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-line py-2 last:border-b-0">
      <dt className="text-small text-ink-2">{label}</dt>
      <dd className="m-0 text-body font-semibold tabular-nums">{value}</dd>
    </div>
  );
}

/** FR-AN-2: owner-only aggregates; the API returns 403 for everyone else. */
export default function AdminPage() {
  const metrics = useAdminMetrics();
  const t = copy.admin;
  const m = metrics.data;
  const forbidden = metrics.error instanceof ApiError && metrics.error.status === 403;

  return (
    <>
      <PageHeader title={t.title} />
      <div className="flex flex-col gap-gap-cards px-screen-x pt-2">
        {metrics.isPending && (
          <p role="status" className="text-small text-muted">
            {copy.common.loading}…
          </p>
        )}
        {metrics.error && (
          <p role="alert" className="text-small text-danger">
            {forbidden ? t.forbidden : copy.common.genericError}
          </p>
        )}
        {m && (
          <>
            <Card>
              <h2 className="m-0 font-display text-h2 font-semibold">{t.funnel}</h2>
              <dl className="m-0">
                {(Object.keys(t.funnelRows) as (keyof typeof t.funnelRows)[]).map((k) => (
                  <Row key={k} label={t.funnelRows[k]} value={m.funnel[k]} />
                ))}
              </dl>
            </Card>
            <Card>
              <dl className="m-0">
                <Row label={t.activation} value={`${m.activation_pct}%`} />
                <Row label={t.conversion} value={`${m.conversion_pct}%`} />
                <Row label={t.warmReplies} value={m.warm_replies_7d} />
                <Row label={t.activeUsers} value={m.active_users_7d} />
                <Row label={t.repliesPerUser} value={m.warm_replies_per_active_user} />
                <Row label={t.aiCost} value={inr.format(m.ai_cost_30d_inr)} />
                <Row
                  label={t.aiCostPerUser}
                  value={inr.format(m.ai_cost_per_active_user_30d_inr)}
                />
                <Row label={t.aiFailures} value={m.ai_failures_30d} />
                <Row label={t.waOut} value={m.wa_messages_out_30d} />
              </dl>
            </Card>
          </>
        )}
      </div>
    </>
  );
}
