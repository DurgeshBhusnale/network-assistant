import type { GoalStrip as GoalStripData } from "@/lib/api/hooks/loop";
import { copy } from "@/lib/copy/en";

/** Indigo hero (v4): sprint label + day, "1 of 4 referrals" with progress, 3 pipeline stats. */
export function GoalStrip({ goal }: { goal: GoalStripData }) {
  const t = copy.today;
  const target = goal.success_target;
  const pct = target ? Math.min(100, Math.round((goal.success_count / target) * 100)) : 0;
  const pipeline = goal.stats.filter((s) => !s.highlight);

  return (
    <section
      aria-label={goal.label}
      className="flex flex-col gap-5 rounded-panel bg-hero p-6 text-on-dark shadow-hero lg:p-7"
    >
      <div className="flex justify-between gap-2 label-caps text-on-dark-muted">
        <span>{goal.label}</span>
        <span>{t.dayOfTotal(goal.day_number, goal.total_days)}</span>
      </div>
      <div>
        <div className="flex items-baseline gap-2.5">
          <span className="font-display text-display leading-none font-semibold tracking-[-0.03em] lg:text-[64px]">
            {goal.success_count}
          </span>
          <span className="text-lead text-on-dark-soft">
            {t.ofTarget(target, goal.success_label)}
          </span>
        </div>
        {target ? (
          <div
            role="progressbar"
            aria-label={goal.success_label}
            aria-valuemin={0}
            aria-valuemax={target}
            aria-valuenow={goal.success_count}
            className="mt-4 h-1 rounded-pill bg-on-dark/15"
          >
            <div className="h-1 rounded-pill bg-grad-soft-bar" style={{ width: `${pct}%` }} />
          </div>
        ) : null}
      </div>
      <dl className="m-0 flex border-t border-on-dark/15 pt-4">
        {pipeline.map((s, i) => (
          <div
            key={s.label}
            className={
              i === 0
                ? "flex flex-1 flex-col-reverse"
                : "flex flex-1 flex-col-reverse border-l border-on-dark/15 pl-4"
            }
          >
            <dt className="mt-0.5 text-caption text-on-dark-muted">{s.label}</dt>
            <dd className="m-0 text-[22px] leading-[26px] font-semibold">{s.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
