"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ComponentType } from "react";

import { copy } from "@/lib/copy/en";

import { cn } from "./cn";
import { ChartIcon, ChatIcon, HomeIcon, MicIcon, PeopleIcon } from "./icons";

type Tab = { href: string; label: string; Icon: ComponentType };

const leftTabs: Tab[] = [
  { href: "/today", label: copy.nav.today, Icon: HomeIcon },
  { href: "/people", label: copy.nav.people, Icon: PeopleIcon },
];
const rightTabs: Tab[] = [
  { href: "/progress", label: copy.nav.progress, Icon: ChartIcon },
  { href: "/replies", label: copy.nav.replies, Icon: ChatIcon },
];

function isActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

function TabLink({ tab, pathname, badge }: { tab: Tab; pathname: string; badge?: number }) {
  const active = isActive(pathname, tab.href);
  return (
    <Link
      href={tab.href}
      aria-current={active ? "page" : undefined}
      className={cn(
        "relative flex min-h-[52px] flex-col items-center justify-start gap-[3px] text-tiny font-semibold tracking-[0.01em] no-underline hover:text-primary",
        active ? "text-primary" : "text-muted",
      )}
    >
      <span
        className={cn(
          "flex h-[30px] w-14 items-center justify-center rounded-pill",
          active && "bg-primary-soft",
        )}
      >
        <tab.Icon />
      </span>
      {tab.label}
      {badge !== undefined && badge > 0 && (
        <span
          aria-label={copy.nav.repliesBadge(badge)}
          className="absolute -top-0.5 left-[calc(50%+6px)] flex h-[18px] min-w-[18px] items-center justify-center rounded-pill bg-ink px-[5px] text-[11px] font-bold text-on-primary shadow-[0_0_0_2px_var(--color-surface)]"
        >
          {badge}
        </span>
      )}
    </Link>
  );
}

export function BottomNav({ repliesCount = 0 }: { repliesCount?: number }) {
  const pathname = usePathname();
  const captureActive = isActive(pathname, "/capture");

  return (
    <nav
      aria-label={copy.nav.label}
      className="fixed inset-x-0 bottom-0 z-10 mx-auto w-full max-w-[480px] border-t border-line bg-surface/95 pb-[env(safe-area-inset-bottom)] backdrop-blur lg:hidden"
    >
      <div className="grid grid-cols-5 items-start px-2 pt-2.5 pb-3">
        {leftTabs.map((tab) => (
          <TabLink key={tab.href} tab={tab} pathname={pathname} />
        ))}
        <Link
          href="/capture"
          aria-label={copy.nav.capture}
          aria-current={captureActive ? "page" : undefined}
          data-testid="capture-fab"
          className="-mt-[26px] flex size-fab items-center justify-center justify-self-center rounded-pill bg-grad text-on-primary shadow-fab hover:text-on-primary"
        >
          <MicIcon size={24} />
        </Link>
        {rightTabs.map((tab) => (
          <TabLink
            key={tab.href}
            tab={tab}
            pathname={pathname}
            badge={tab.href === "/replies" ? repliesCount : undefined}
          />
        ))}
      </div>
    </nav>
  );
}
