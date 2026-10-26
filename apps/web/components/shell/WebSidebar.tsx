"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ComponentType } from "react";

import { cn } from "@/components/ui/cn";
import { ChartIcon, ChatIcon, HomeIcon, MicIcon, PeopleIcon } from "@/components/ui/icons";
import { useActiveGoal, useMe, usePacks } from "@/lib/api/hooks/account";
import { copy } from "@/lib/copy/en";

type Tab = { href: string; label: string; Icon: ComponentType<{ size?: number }> };

const TABS: Tab[] = [
  { href: "/today", label: copy.nav.today, Icon: HomeIcon },
  { href: "/people", label: copy.nav.people, Icon: PeopleIcon },
  { href: "/progress", label: copy.nav.progress, Icon: ChartIcon },
  { href: "/replies", label: copy.nav.replies, Icon: ChatIcon },
];

function isActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

/** Desktop navigation (ADR-0011): 248 px column replacing the bottom nav from `lg` up. */
export function WebSidebar({ repliesCount = 0 }: { repliesCount?: number }) {
  const pathname = usePathname();
  const me = useMe();
  const goal = useActiveGoal().data;
  const pack = usePacks().data?.find((p) => p.id === goal?.pack_id);
  const name = me.data?.display_name ?? me.data?.email ?? "";

  return (
    <aside className="fixed inset-y-0 left-0 z-10 hidden w-[var(--sidebar-width)] flex-col border-r border-line bg-surface px-5 pt-7 pb-6 lg:flex">
      <Link
        href="/today"
        className="flex h-10 items-center gap-3 px-2 text-ink no-underline hover:text-ink"
      >
        <span aria-hidden="true" className="size-8 rounded-[10px] bg-grad" />
        <span className="font-display text-[20px] font-semibold tracking-[-0.02em]">
          {copy.appName}
        </span>
      </Link>

      <Link
        href="/capture"
        className="mt-7 flex h-[52px] items-center justify-center gap-2.5 rounded-button bg-grad text-[15px] font-semibold text-on-primary no-underline shadow-cta hover:text-on-primary"
      >
        <MicIcon size={20} />
        {copy.nav.voiceCapture}
      </Link>

      <nav aria-label={copy.nav.label} className="mt-6 flex flex-col gap-1">
        {TABS.map((tab) => {
          const active = isActive(pathname, tab.href);
          const badge = tab.href === "/replies" && repliesCount > 0 ? repliesCount : null;
          return (
            <Link
              key={tab.href}
              href={tab.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex h-12 items-center gap-3.5 rounded-[14px] px-3.5 text-[15px] font-semibold no-underline",
                active
                  ? "bg-primary-soft text-primary hover:text-primary"
                  : "text-muted hover:bg-surface-2 hover:text-ink",
              )}
            >
              <tab.Icon size={22} />
              <span className="flex-1">{tab.label}</span>
              {badge !== null && (
                <span
                  aria-label={copy.nav.repliesBadge(badge)}
                  className="flex h-[22px] min-w-[22px] items-center justify-center rounded-pill bg-ink px-1.5 text-label font-bold text-on-primary"
                >
                  {badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      <div className="flex-1" />

      <Link
        href="/settings"
        aria-label={copy.common.settings}
        className="flex items-center gap-3 border-t border-line pt-5 text-ink no-underline hover:text-ink"
      >
        <span className="flex size-10 shrink-0 items-center justify-center rounded-pill bg-primary-soft font-bold text-primary">
          {name.trim().charAt(0).toUpperCase() || "·"}
        </span>
        <span className="flex min-w-0 flex-col">
          <span className="truncate text-[15px] leading-5 font-semibold">
            {me.data?.display_name ?? copy.settings.title}
          </span>
          {goal && (
            <span className="truncate text-caption leading-[18px] text-muted">
              {copy.nav.sprintDay(pack?.name ?? "", goal.day_number)}
            </span>
          )}
        </span>
      </Link>
    </aside>
  );
}
