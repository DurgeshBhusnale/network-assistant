import { cn } from "@/components/ui/cn";
import type { GoalStrip as GoalStripData } from "@/lib/api/hooks/loop";
import { copy } from "@/lib/copy/en";

/** Dark goal panel: label, days left, goal title, 4 stats (FR-TODAY-3). */
export function GoalStrip({ goal }: { goal: GoalStripData }) {
  const t = copy.today;
  return (
    <section
      aria-label={goal.label}
      className="flex flex-col gap-3 rounded-panel bg-surface-dark p-4 text-on-dark"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-caption tracking-[0.06em] text-on-dark-muted uppercase">
          {t.dayOf(goal.label, goal.day_number, goal.total_days)}
        </span>
        {goal.days_left !== null && (
          <span className="rounded-pill bg-accent px-2 py-[3px] text-caption font-semibold text-on-accent">
            {t.daysLeft(goal.days_left)}
          </span>
        )}
      </div>
      <div className="font-display text-h2 font-semibold">{goal.title}</div>
      <dl className="m-0 grid grid-cols-4 gap-2">
        {goal.stats.map((s) => (
          <div key={s.label} className="flex flex-col-reverse">
            <dt className="text-tiny text-on-dark-muted">{s.label}</dt>
            <dd className={cn("m-0 text-[20px] font-semibold", s.highlight && "text-accent")}>
              {s.value}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
