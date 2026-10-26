"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/shell/PageHeader";
import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { useContacts } from "@/lib/api/hooks/people";
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

export default function PeoplePage() {
  const [search, setSearch] = useState("");
  const q = useDebounced(search.trim(), 250);
  const contacts = useContacts(q);
  const items = contacts.data?.pages.flatMap((p) => p.items) ?? [];

  return (
    <>
      <PageHeader title={t.title} />
      <div className="flex flex-col gap-3 px-screen-x pt-2">
        <div className="flex gap-2">
          <Link
            href="/people/import"
            className="inline-flex min-h-tap flex-1 items-center justify-center rounded-button bg-primary px-4 text-[14px] font-semibold text-on-primary no-underline"
          >
            {t.add}
          </Link>
          <Link
            href="/people/new"
            className="inline-flex min-h-tap items-center justify-center rounded-button border border-line bg-surface px-4 text-[14px] font-semibold text-ink no-underline"
          >
            {t.addByHand}
          </Link>
        </div>

        <label htmlFor="people-search" className="sr-only">
          {t.searchLabel}
        </label>
        <input
          id="people-search"
          type="search"
          value={search}
          placeholder={t.searchPlaceholder}
          onChange={(e) => setSearch(e.target.value)}
          className="h-[46px] rounded-button border border-line-strong bg-surface px-3 text-body"
        />

        {contacts.isPending ? (
          <p className="text-small text-muted" role="status">
            {copy.common.loading}…
          </p>
        ) : items.length === 0 ? (
          q ? (
            <p className="text-small text-muted">{t.noResults(q)}</p>
          ) : (
            <EmptyState
              title={t.emptyTitle}
              body={t.emptyBody}
              action={
                <Link href="/people/import" className="font-semibold">
                  {t.import}
                </Link>
              }
            />
          )
        ) : (
          <ul className="m-0 flex list-none flex-col rounded-card border border-line bg-surface p-0">
            {items.map((c) => (
              <li key={c.id} className="border-b border-line-soft last:border-b-0">
                <Link
                  href={`/people/${c.id}`}
                  className="flex min-h-[60px] items-center gap-3 px-card py-2 text-ink no-underline"
                >
                  <Avatar name={c.full_name} />
                  <span className="flex min-w-0 flex-col">
                    <span className="truncate text-body font-semibold">{c.full_name}</span>
                    {(c.title || c.company) && (
                      <span className="truncate text-small text-muted">
                        {[c.title, c.company].filter(Boolean).join(" · ")}
                      </span>
                    )}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}

        {contacts.hasNextPage && (
          <Button
            variant="secondary"
            loading={contacts.isFetchingNextPage}
            onClick={() => void contacts.fetchNextPage()}
          >
            {t.loadMore}
          </Button>
        )}
      </div>
    </>
  );
}
