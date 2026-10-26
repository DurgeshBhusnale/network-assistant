"use client";

import type { ReactNode } from "react";

import { BottomNav } from "@/components/ui/BottomNav";
import { useRepliesPending } from "@/lib/api/hooks/loop";

/** Phone-first column (desktop centres a 480 px column) with the bottom nav. */
export function AppShell({ children }: { children: ReactNode }) {
  const replies = useRepliesPending();
  return (
    <>
      <main className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col pb-[calc(var(--nav-height)+env(safe-area-inset-bottom)+16px)]">
        {children}
      </main>
      <BottomNav repliesCount={replies.data?.items.length ?? 0} />
    </>
  );
}
