"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { BottomNav } from "@/components/ui/BottomNav";
import { cn } from "@/components/ui/cn";
import { useRepliesPending } from "@/lib/api/hooks/loop";

/** The four tab screens show the bottom nav; detail screens (draft, person, capture, settings)
 * use their own back control and bottom action bar, as in the v4 design. */
const TAB_ROOTS = ["/today", "/people", "/progress", "/replies"];

export function showsBottomNav(pathname: string): boolean {
  return TAB_ROOTS.includes(pathname);
}

/** Phone-first column (desktop centres a 480 px column). */
export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const withNav = showsBottomNav(pathname);
  const replies = useRepliesPending();
  return (
    <>
      <main
        className={cn(
          "mx-auto flex min-h-dvh w-full max-w-[480px] flex-col",
          withNav ? "pb-[calc(var(--nav-height)+env(safe-area-inset-bottom)+24px)]" : "pb-12",
        )}
      >
        {children}
      </main>
      {withNav && <BottomNav repliesCount={replies.data?.items.length ?? 0} />}
    </>
  );
}
