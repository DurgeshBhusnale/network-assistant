import type { ReactNode } from "react";

import { cn } from "./cn";

/**
 * Action bar pinned to the bottom of detail screens (draft, onboarding, upgrade).
 * "solid": white with a hairline top (draft, upgrade); "fade": canvas fade (onboarding).
 * Pages using it add bottom padding (`pb-bar` / `pb-bar-lg`) so content can scroll clear of it.
 */
export function BottomBar({
  children,
  variant = "solid",
}: {
  children: ReactNode;
  variant?: "solid" | "fade";
}) {
  return (
    <div
      className={cn(
        "fixed inset-x-0 bottom-0 z-10 mx-auto flex w-full max-w-[480px] flex-col gap-3 px-screen-x pt-4 pb-[calc(env(safe-area-inset-bottom)+24px)]",
        variant === "solid"
          ? "border-t border-line bg-surface/95 backdrop-blur"
          : "bg-[linear-gradient(180deg,transparent,var(--color-bg)_30%)]",
      )}
    >
      {children}
    </div>
  );
}
