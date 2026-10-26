"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Avatar } from "@/components/ui/Avatar";
import { Button, buttonClasses } from "@/components/ui/Button";
import { cn } from "@/components/ui/cn";
import { EmptyState } from "@/components/ui/EmptyState";
import { PeopleIcon, PlusIcon, SearchIcon } from "@/components/ui/icons";
import { useContacts, type ContactSummary } from "@/lib/api/hooks/people";
import { copy } from "@/lib/copy/en";

const t = copy.people;

function useDebounced(value: string, ms: number): string {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), ms);
    return () => window.clearTimeout(timer);
  }, [value, ms]);
  return debounced;
}

/** A–Z groups in list order (the API sorts by name). Non-letters go under "#". */
function groupByLetter(
  items: ContactSummary[],
): Array<{ letter: string; items: ContactSummary[] }> {
  const groups: Array<{ letter: string; items: ContactSummary[] }> = [];
  for (const c of items) {
    const first = c.full_name.trim().charAt(0).toUpperCase();
    const letter = /[A-Z]/.test(first) ? first : "#";
    const last = groups[groups.length - 1];
    if (last && last.letter === letter) last.items.push(c);
    else groups.push({ letter, items: [c] });
  }
  return groups;
}

export default function PeoplePage() {
  const [search, setSearch] = useState("");
  const q = useDebounced(search.trim(), 250);
  const contacts = useContacts(q);
  const items = useMemo(() => contacts.data?.pages.flatMap((p) => p.items) ?? [], [contacts.data]);
  const total = contacts.data?.pages[0]?.total ?? null;
  const groups = useMemo(() => groupByLetter(items), [items]);
  const noneAtAll = !contacts.isPending && items.length === 0 && !q && total === 0;

  return (
    <div className="flex flex-1 flex-col gap-5 px-screen-x pt-6 lg:gap-6 lg:pt-10">
      <header className="flex items-center justify-between gap-3 lg:items-end">
        <div className="flex flex-col">
          <h1 className="m-0 title-lg">{t.title}</h1>
          {total !== null && total > 0 && (
            <span className="mt-0.5 hidden text-body text-muted lg:block">{t.count(total)}</span>
          )}
        </div>
        <div className="flex items-center gap-3 lg:hidden">
          {total !== null && total > 0 && (
            <span className="text-small text-muted">{t.count(total)}</span>
          )}
          <Link
            href="/people/import"
            aria-label={t.add}
            className="inline-flex size-tap items-center justify-center rounded-pill bg-primary-soft text-primary no-underline hover:text-primary"
          >
            <PlusIcon size={20} />
          </Link>
        </div>
        <div className="hidden items-center gap-3 lg:flex">
          <Link href="/people/import" className={buttonClasses({ variant: "secondary" })}>
            {t.importContacts}
          </Link>
          <Link href="/people/new" className={buttonClasses({ variant: "tonal" })}>
            {t.addByHand}
          </Link>
        </div>
      </header>

      {!noneAtAll && (
        <div
          className={cn(
            "flex h-field items-center gap-3 rounded-button-lg px-4 text-muted lg:w-[420px]",
            search ? "bg-surface ring-selected" : "bg-field",
          )}
        >
          <SearchIcon size={20} />
          <label htmlFor="people-search" className="sr-only">
            {t.searchLabel}
          </label>
          <input
            id="people-search"
            type="search"
            value={search}
            placeholder={t.searchPlaceholder}
            onChange={(e) => setSearch(e.target.value)}
            className="h-full min-w-0 flex-1 bg-transparent text-[16px] text-ink placeholder:text-muted focus:outline-none"
          />
        </div>
      )}

      {contacts.isPending ? (
        <p className="text-small text-muted" role="status">
          {copy.common.loading}…
        </p>
      ) : items.length === 0 ? (
        q ? (
          <EmptyState
            title={t.noResults(q)}
            body={t.noResultsBody}
            action={
              <Link href="/people/new" className={buttonClasses({ variant: "tonal" })}>
                {t.addByHand}
              </Link>
            }
          />
        ) : (
          <EmptyState
            Icon={PeopleIcon}
            title={t.emptyTitle}
            body={t.emptyBody}
            action={
              <>
                <Link href="/people/import" className={buttonClasses({ size: "lg" })}>
                  {t.import}
                </Link>
                <Link
                  href="/people/new"
                  className="flex h-11 items-center text-body font-semibold no-underline"
                >
                  {t.addByHand}
                </Link>
              </>
            }
          />
        )
      ) : (
        <>
          <div className="hidden rounded-card bg-surface px-7 pt-2 pb-3 shadow-[0_0_0_1px_var(--color-line)] lg:block">
            <div
              aria-hidden="true"
              className="grid h-12 grid-cols-[2fr_1.4fr_1.6fr] items-center border-b border-line label-caps text-muted"
            >
              <span>{t.colName}</span>
              <span>{t.colCompany}</span>
              <span>{t.colRole}</span>
            </div>
            {groups.map((g) => (
              <section key={g.letter} aria-label={g.letter}>
                <h2 className="m-0 pt-4 pb-1 label-caps text-primary">{g.letter}</h2>
                {g.items.map((c) => (
                  <Link
                    key={c.id}
                    href={`/people/${c.id}`}
                    className="grid h-16 grid-cols-[2fr_1.4fr_1.6fr] items-center border-b border-surface-2 text-ink no-underline hover:bg-surface-2 hover:text-ink"
                  >
                    <span className="flex min-w-0 items-center gap-4">
                      <Avatar name={c.full_name} size="sm" />
                      <span className="truncate text-[16px] font-semibold">{c.full_name}</span>
                    </span>
                    <span className="truncate pr-4 text-body text-ink-2">{c.company ?? "—"}</span>
                    <span className="truncate pr-4 text-body text-muted">{c.title ?? "—"}</span>
                  </Link>
                ))}
              </section>
            ))}
          </div>
          <div className="flex flex-col lg:hidden">
            {groups.map((g) => (
              <section key={g.letter} aria-label={g.letter} className="flex flex-col">
                <h2 className="m-0 pt-3 pb-1 label-caps text-primary">{g.letter}</h2>
                <ul className="m-0 flex list-none flex-col p-0">
                  {g.items.map((c) => (
                    <li key={c.id}>
                      <Link
                        href={`/people/${c.id}`}
                        className="flex h-[68px] items-center gap-4 text-ink no-underline hover:text-ink"
                      >
                        <Avatar name={c.full_name} size="md" />
                        <span className="flex h-full min-w-0 flex-1 flex-col justify-center border-b border-line">
                          <span className="truncate text-[16px] leading-[22px] font-semibold">
                            {c.full_name}
                          </span>
                          {(c.company || c.title) && (
                            <span className="truncate text-small leading-5 text-muted">
                              {c.company ?? c.title}
                            </span>
                          )}
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
        </>
      )}

      {contacts.hasNextPage && (
        <Button
          variant="secondary"
          className="lg:self-center lg:px-10"
          loading={contacts.isFetchingNextPage}
          onClick={() => void contacts.fetchNextPage()}
        >
          {t.loadMore}
        </Button>
      )}
    </div>
  );
}
