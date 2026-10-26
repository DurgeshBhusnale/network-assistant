"use client";

import Link from "next/link";

import { GoalStrip } from "@/components/today/GoalStrip";
import { PersonCard } from "@/components/today/PersonCard";
import { buttonClasses } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { PeopleIcon } from "@/components/ui/icons";
import { useMe } from "@/lib/api/hooks/account";
import { useToday } from "@/lib/api/hooks/loop";
import { copy } from "@/lib/copy/en";
import { useNow } from "@/lib/device/useNow";

const t = copy.today;
const dateFmt = new Intl.DateTimeFormat("en-IN", {
  weekday: "long",
  day: "numeric",
  month: "long",
});

function initial(name: string | null | undefined): string {
  return (name ?? "").trim().charAt(0).toUpperCase() || "·";
}

export default function TodayPage() {
  const today = useToday();
  const me = useMe();
  const data = today.data;
  const now = useNow();
  const open = data?.items.filter((i) => i.status !== "sent").length ?? 0;
  const noContacts = data && data.goal && data.contacts_count === 0;
  const hasList = Boolean(data && data.items.length > 0);

  return (
    <div className="flex flex-1 flex-col gap-section px-screen-x pt-6 lg:gap-8 lg:pt-10">
      <header className="flex items-center justify-between gap-3 lg:items-end">
        <div className="flex min-w-0 flex-col">
          <span className="text-small text-muted lg:text-body">
            {now ? dateFmt.format(now) : " "}
          </span>
          <h1 className="m-0 mt-0.5 title lg:mt-1">
            {t.greeting(now?.getHours() ?? 9, data?.display_name ?? null)}
          </h1>
        </div>
        {hasList && open > 0 && (
          <span className="hidden text-body text-muted lg:block">
            {t.desktopMeta(open, data?.minutes ?? 0)}
          </span>
        )}
        <Link
          href="/settings"
          aria-label={copy.common.settings}
          className="inline-flex size-11 shrink-0 items-center justify-center rounded-pill bg-primary-soft font-bold text-primary no-underline hover:text-primary lg:hidden"
        >
          {initial(data?.display_name ?? me.data?.display_name ?? me.data?.email)}
        </Link>
      </header>

      {today.isPending && (
        <p role="status" className="m-0 text-small text-muted">
          {copy.common.loading}…
        </p>
      )}
      {today.isError && (
        <p role="alert" className="m-0 text-small text-danger">
          {copy.common.genericError}
        </p>
      )}

      {data && !data.goal && (
        <EmptyState
          Icon={PeopleIcon}
          title={t.noGoalTitle}
          body={t.noGoalBody}
          action={
            <Link href="/onboarding/goal" className={buttonClasses({ size: "lg" })}>
              {t.noGoalAction}
            </Link>
          }
        />
      )}
      {noContacts && (
        <EmptyState
          Icon={PeopleIcon}
          title={t.noContactsTitle}
          body={t.noContactsBody}
          action={
            <>
              <Link href="/people/import" className={buttonClasses({ size: "lg" })}>
                {t.noContactsAction}
              </Link>
              <Link
                href="/capture"
                className="flex h-11 items-center text-body font-semibold no-underline"
              >
                {t.orSpeak}
              </Link>
            </>
          }
        />
      )}

      {data?.goal && !noContacts && (
        <div className="flex flex-col gap-section lg:grid lg:grid-cols-[minmax(0,1fr)_360px] lg:items-start lg:gap-8">
          <aside className="flex flex-col gap-5 lg:order-2">
            <GoalStrip goal={data.goal} />
            <section className="hidden flex-col gap-4 rounded-card bg-surface p-6 hairline lg:flex">
              <div>
                <h2 className="m-0 text-[17px] leading-[22px] font-semibold">{t.metTitle}</h2>
                <p className="m-0 mt-1 text-small leading-[21px] text-muted">{t.metBody}</p>
              </div>
              <Link
                href="/capture"
                className={buttonClasses({ variant: "tonal", fullWidth: true })}
              >
                {t.metAction}
              </Link>
            </section>
          </aside>

          {hasList && (
            <section
              aria-labelledby="todays-people"
              className="flex flex-col gap-gap-cards lg:order-1 lg:gap-5"
            >
              <div className="flex items-baseline justify-between gap-2">
                <h2
                  id="todays-people"
                  className="m-0 text-h2 font-semibold tracking-[-0.01em] lg:label-caps lg:text-muted"
                >
                  {t.heading(data.weekly)}
                </h2>
                {open > 0 && (
                  <span className="text-small text-muted lg:hidden">
                    {t.countMinutes(open, data.minutes)}
                  </span>
                )}
              </div>
              {data.done && (
                <div className="flex flex-col gap-1 rounded-card bg-info p-card">
                  <span className="text-[16px] font-semibold">{t.doneTitle}</span>
                  <span className="text-small text-ink-2">{t.doneBody}</span>
                  <Link href="/capture" className="mt-1 self-start text-small font-semibold">
                    {t.doneAction}
                  </Link>
                </div>
              )}
              <div className="flex flex-col gap-gap-cards lg:grid lg:grid-cols-2 lg:gap-5">
                {data.items.map((item) => (
                  <PersonCard key={item.id} item={item} />
                ))}
              </div>
              {data.weekly && <p className="m-0 text-caption text-muted">{t.weeklyNote}</p>}
            </section>
          )}
          {data.contacts_count > 0 && data.items.length === 0 && (
            <div className="lg:order-1">
              <EmptyState Icon={PeopleIcon} title={t.emptyTitle} body={t.emptyBody} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
