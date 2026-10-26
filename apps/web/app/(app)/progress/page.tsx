"use client";

import Link from "next/link";

import { buttonClasses } from "@/components/ui/Button";
import { cn } from "@/components/ui/cn";
import { EmptyState } from "@/components/ui/EmptyState";
import { ChartIcon } from "@/components/ui/icons";
import { SectionLabel } from "@/components/ui/SectionLabel";
import { useProgress } from "@/lib/api/hooks/loop";
import { copy } from "@/lib/copy/en";

const t = copy.progressPage;

/** Bars run lightest → strongest; the success step uses the accent gradient. */
const BAR = ["bg-bar-1", "bg-bar-2", "bg-bar-3"] as const;

export default function ProgressPage() {
  const progress = useProgress();
  const data = progress.data;
  const goal = data?.goal;
  const first = data?.funnel[0]?.count ?? 0;
  const target = goal?.success_target;
  const pct = goal && target ? Math.min(100, Math.round((goal.success_count / target) * 100)) : 0;

  return (
    <div className="flex flex-col gap-section px-screen-x pt-6">
      <h1 className="sr-only">{t.title}</h1>
      {progress.isPending && (
        <p role="status" className="text-small text-muted">
          {copy.common.loading}…
        </p>
      )}
      {data && !goal && (
        <EmptyState
          Icon={ChartIcon}
          title={t.title}
          body={t.noGoal}
          action={
            <Link href="/onboarding/goal" className={buttonClasses({ size: "lg" })}>
              {copy.today.noGoalAction}
            </Link>
          }
        />
      )}
      {data && goal && (
        <>
          <section aria-label={goal.success_label}>
            <SectionLabel as="p">{t.sprintDay(goal.label, goal.day_number)}</SectionLabel>
            <div className="mt-2.5 flex items-baseline gap-3">
              <span className="font-display text-[64px] leading-none font-semibold tracking-[-0.04em] text-grad">
                {target ? t.countOf(goal.success_count, target) : goal.success_count}
              </span>
              <span className="text-[18px] text-muted">{goal.success_label.toLowerCase()}</span>
            </div>
            {target ? (
              <div className="mt-5 h-1.5 rounded-pill bg-line" aria-hidden="true">
                <div className="h-1.5 rounded-pill bg-grad-bar" style={{ width: `${pct}%` }} />
              </div>
            ) : null}
            {data.headline && <p className="m-0 mt-3 text-small text-muted">{data.headline}</p>}
          </section>

          <div className="flex gap-3">
            <Stat value={data.warm_replies_this_week} label={t.warmReplies} />
            <Stat value={goal.days_left ?? "–"} label={t.daysLeft} />
          </div>

          <section className="flex flex-col gap-4">
            <SectionLabel>{t.pipeline}</SectionLabel>
            <ul className="m-0 flex list-none flex-col gap-4 p-0">
              {data.funnel.map((step, i) => {
                const width = first > 0 ? Math.round((step.count / first) * 100) : 0;
                return (
                  <li key={step.key} className="flex items-center gap-3.5">
                    <span className="w-[84px] shrink-0 text-small text-ink-2">{step.label}</span>
                    <span className="h-2.5 flex-1 rounded-pill bg-bar-track" aria-hidden="true">
                      <span
                        className={cn(
                          "block h-full rounded-pill",
                          step.highlight || i >= BAR.length ? "bg-grad-bar" : BAR[i],
                        )}
                        style={{ width: `${Math.min(100, width)}%` }}
                      />
                    </span>
                    <span className="w-6 text-right text-body font-semibold">{step.count}</span>
                  </li>
                );
              })}
            </ul>
          </section>

          {data.by_company.length > 0 && (
            <section className="flex flex-col">
              <SectionLabel className="mb-1">{t.byCompany}</SectionLabel>
              <ul className="m-0 flex list-none flex-col p-0">
                {data.by_company.map((c) => (
                  <li
                    key={c.company}
                    className="flex min-h-[68px] items-center justify-between gap-3 border-b border-line"
                  >
                    <span className="flex min-w-0 flex-col">
                      <span className="truncate text-[16px] leading-[22px] font-semibold">
                        {c.company}
                      </span>
                      <span className="text-caption leading-[18px] text-muted">
                        {t.people(c.people)}
                      </span>
                    </span>
                    <span
                      className={cn(
                        "inline-flex h-6 shrink-0 items-center rounded-badge px-2.5 text-label font-semibold",
                        c.reached
                          ? "bg-[var(--color-info-from)] text-info-text"
                          : "bg-badge-neutral text-badge-neutral-text",
                      )}
                    >
                      {c.status}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </div>
  );
}

function Stat({ value, label }: { value: number | string; label: string }) {
  return (
    <div className="flex flex-1 flex-col rounded-card bg-surface p-card hairline">
      <span className="font-display text-[36px] leading-10 font-semibold tracking-[-0.02em]">
        {value}
      </span>
      <span className="mt-1 text-small leading-5 text-muted">{label}</span>
    </div>
  );
}
