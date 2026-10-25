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
        "relative flex min-h-tap flex-col items-center justify-center gap-0.5 text-tiny no-underline",
        active ? "font-semibold text-primary" : "text-muted",
      )}
    >
      <tab.Icon />
      {tab.label}
      {badge !== undefined && badge > 0 && (
        <span
          aria-label={copy.nav.repliesBadge(badge)}
          className="absolute -top-1 right-[18px] flex h-[18px] min-w-[18px] items-center justify-center rounded-pill bg-danger px-1 text-[11px] font-semibold text-on-primary"
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
      className="fixed inset-x-0 bottom-0 z-10 mx-auto w-full max-w-[480px] border-t border-line bg-surface pb-[env(safe-area-inset-bottom)]"
    >
      <div className="grid h-nav grid-cols-5 items-center">
        {leftTabs.map((tab) => (
          <TabLink key={tab.href} tab={tab} pathname={pathname} />
        ))}
        <Link
          href="/capture"
          aria-label={copy.nav.capture}
          aria-current={captureActive ? "page" : undefined}
          data-testid="capture-fab"
          className="-mt-6 flex size-fab items-center justify-center justify-self-center rounded-pill bg-accent text-on-accent shadow-fab"
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
