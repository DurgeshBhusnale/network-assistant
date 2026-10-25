"use client";

import Link from "next/link";

import { PageHeader } from "@/components/shell/PageHeader";
import { Card } from "@/components/ui/Card";
import { cn } from "@/components/ui/cn";
import { EmptyState } from "@/components/ui/EmptyState";
import { useProgress } from "@/lib/api/hooks/loop";
import { copy } from "@/lib/copy/en";

const t = copy.progressPage;

export default function ProgressPage() {
  const progress = useProgress();
  const data = progress.data;
  const first = data?.funnel[0]?.count ?? 0;

  return (
    <>
      <PageHeader
        title={data?.headline ?? t.title}
        eyebrow={
          data?.goal
            ? copy.today.dayOf(data.goal.label, data.goal.day_number, data.goal.total_days)
            : undefined
        }
      />
      <div className="flex flex-col gap-gap-cards px-screen-x pt-2">
        {progress.isPending && (
          <p role="status" className="text-small text-muted">
            {copy.common.loading}…
          </p>
        )}
        {data && !data.goal && (
          <EmptyState
            title={t.title}
            body={t.noGoal}
            action={
              <Link href="/onboarding/goal" className="font-semibold">
                {copy.today.noGoalAction}
              </Link>
            }
          />
        )}
        {data?.goal && (
          <>
            <div className="grid grid-cols-2 gap-gap-cards">
              <div className="flex flex-col gap-1 rounded-panel bg-surface-dark p-4 text-on-dark">
                <span className="font-display text-[32px] font-bold">
                  {data.warm_replies_this_week}
                </span>
                <span className="text-small text-on-dark-muted">{t.warmReplies}</span>
              </div>
              <div className="flex flex-col gap-1 rounded-panel border border-line bg-surface p-4">
                <span className="font-display text-[32px] font-bold">
                  {data.goal.days_left ?? "–"}
                </span>
                <span className="text-small text-muted">{t.daysLeft}</span>
              </div>
            </div>

            <Card>
              <h2 className="m-0 font-display text-h2 font-semibold">{t.pipeline}</h2>
              <ul className="m-0 flex list-none flex-col gap-2.5 p-0">
                {data.funnel.map((step) => {
                  const width = first > 0 ? Math.max(4, Math.round((step.count / first) * 100)) : 4;
                  return (
                    <li key={step.key} className="flex items-center gap-2">
                      <span className="w-[92px] shrink-0 text-small">{step.label}</span>
                      <span className="h-2.5 flex-1 rounded-pill bg-bg" aria-hidden="true">
                        <span
                          className={cn(
                            "block h-full rounded-pill",
                            step.highlight ? "bg-accent" : "bg-primary",
                          )}
                          style={{ width: `${Math.min(100, width)}%` }}
                        />
                      </span>
                      <span className="w-6 text-right text-small font-semibold">{step.count}</span>
                    </li>
                  );
                })}
              </ul>
            </Card>

            {data.by_company.length > 0 && (
              <Card>
                <h2 className="m-0 font-display text-h2 font-semibold">{t.byCompany}</h2>
                <ul className="m-0 flex list-none flex-col p-0">
                  {data.by_company.map((c) => (
                    <li
                      key={c.company}
                      className="flex min-h-tap items-center justify-between gap-2 border-b border-line-soft last:border-b-0"
                    >
                      <span className="text-body font-semibold">{c.company}</span>
                      <span className="text-small text-muted">{c.status}</span>
                    </li>
                  ))}
                </ul>
              </Card>
            )}
          </>
        )}
      </div>
    </>
  );
}
