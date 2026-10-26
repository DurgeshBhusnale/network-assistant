"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { WebSidebar } from "@/components/shell/WebSidebar";
import { BottomNav } from "@/components/ui/BottomNav";
import { cn } from "@/components/ui/cn";
import { useRepliesPending } from "@/lib/api/hooks/loop";

/** Phone: the four tab screens show the bottom nav; detail screens (draft, person, capture,
 * settings) use their own back control and bottom action bar, as in the v4 design. */
const TAB_ROOTS = ["/today", "/people", "/progress", "/replies"];

export function showsBottomNav(pathname: string): boolean {
  return TAB_ROOTS.includes(pathname);
}

/** Desktop (ADR-0011): every screen gets the sidebar, except full-bleed voice capture. */
export function showsSidebar(pathname: string): boolean {
  return pathname !== "/capture";
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const withNav = showsBottomNav(pathname);
  const withSidebar = showsSidebar(pathname);
  const replies = useRepliesPending();
  const repliesCount = replies.data?.items.length ?? 0;
  return (
    <>
      {withSidebar && <WebSidebar repliesCount={repliesCount} />}
      <main
        className={cn(
          "mx-auto flex min-h-dvh w-full max-w-[480px] flex-col",
          withNav ? "pb-[calc(var(--nav-height)+env(safe-area-inset-bottom)+24px)]" : "pb-12",
          withSidebar
            ? "lg:mr-0 lg:ml-[var(--sidebar-width)] lg:w-[calc(100%-var(--sidebar-width))] lg:max-w-[1200px] lg:pb-12"
            : "lg:max-w-none",
        )}
      >
        {children}
      </main>
      {withNav && <BottomNav repliesCount={repliesCount} />}
    </>
  );
}
