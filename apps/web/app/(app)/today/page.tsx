"use client";

import Link from "next/link";

import { GoalStrip } from "@/components/today/GoalStrip";
import { PersonCard } from "@/components/today/PersonCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { UserIcon } from "@/components/ui/icons";
import { useToday } from "@/lib/api/hooks/loop";
import { copy } from "@/lib/copy/en";
import { useNow } from "@/lib/device/useNow";

const t = copy.today;
const dateFmt = new Intl.DateTimeFormat("en-IN", {
  weekday: "long",
  day: "numeric",
  month: "long",
});

export default function TodayPage() {
  const today = useToday();
  const data = today.data;
  const now = useNow();
  const open = data?.items.filter((i) => i.status !== "sent").length ?? 0;

  return (
    <div className="flex flex-col gap-gap-cards">
      <header className="flex items-start justify-between px-screen-x pt-6 pb-1">
        <div className="flex flex-col gap-0.5">
          <span className="text-small text-muted">{now ? dateFmt.format(now) : " "}</span>
          <h1 className="m-0 font-display text-h1 font-bold tracking-[-0.01em]">
            {t.greeting(now?.getHours() ?? 9, data?.display_name ?? null)}
          </h1>
        </div>
        <Link
          href="/settings"
          aria-label={copy.common.settings}
          className="inline-flex size-tap items-center justify-center rounded-pill border border-line bg-surface text-ink no-underline"
        >
          <UserIcon />
        </Link>
      </header>

      <div className="flex flex-col gap-gap-cards px-screen-x">
        {today.isPending && (
          <p role="status" className="text-small text-muted">
            {copy.common.loading}…
          </p>
        )}
        {today.isError && (
          <p role="alert" className="text-small text-danger">
            {copy.common.genericError}
          </p>
        )}
        {data?.goal && <GoalStrip goal={data.goal} />}

        {data && !data.goal && (
          <EmptyState
            title={t.noGoalTitle}
            body={t.noGoalBody}
            action={
              <Link href="/onboarding/goal" className="font-semibold">
                {t.noGoalAction}
              </Link>
            }
          />
        )}
        {data && data.goal && data.contacts_count === 0 && (
          <EmptyState
            title={t.noContactsTitle}
            body={t.noContactsBody}
            action={
              <Link href="/people/import" className="font-semibold">
                {t.noContactsAction}
              </Link>
            }
          />
        )}

        {data && data.items.length > 0 && (
          <div className="flex items-baseline justify-between pt-2">
            <h2 className="m-0 font-display text-h2 font-semibold">
              {t.heading(open, data.weekly)}
            </h2>
            {open > 0 && <span className="text-small text-muted">{t.minutes(data.minutes)}</span>}
          </div>
        )}
        {data?.done && (
          <EmptyState
            title={t.doneTitle}
            body={t.doneBody}
            action={
              <Link href="/capture" className="font-semibold">
                {t.doneAction}
              </Link>
            }
          />
        )}
        {data?.items.map((item) => (
          <PersonCard key={item.id} item={item} />
        ))}
        {data && data.goal && data.contacts_count > 0 && data.items.length === 0 && (
          <EmptyState title={t.emptyTitle} body={t.emptyBody} />
        )}
        {data?.weekly && data.items.length > 0 && (
          <p className="text-caption text-muted">{t.weeklyNote}</p>
        )}
      </div>
    </div>
  );
}
