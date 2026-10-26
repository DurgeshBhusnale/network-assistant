import type { ReactNode } from "react";

import { cn } from "./cn";

const DESKTOP = {
  /** Draft: a white card in the right column. */
  card: "lg:sticky lg:top-10 lg:mx-0 lg:max-w-none lg:gap-3.5 lg:rounded-panel lg:border-0 lg:bg-surface lg:p-7 lg:shadow-panel lg:backdrop-blur-none",
  /** Onboarding: white footer to the right of the indigo panel, button aligned right. */
  footer:
    "lg:left-[480px] lg:mx-0 lg:h-[104px] lg:w-auto lg:max-w-none lg:flex-row lg:items-center lg:justify-end lg:border-t lg:border-line lg:bg-surface lg:bg-none lg:px-[72px] lg:py-0 lg:[&>button]:w-auto lg:[&>button]:px-12",
  /** Upgrade: plain buttons in the left column. */
  inline:
    "lg:static lg:mx-0 lg:max-w-[520px] lg:border-0 lg:bg-transparent lg:p-0 lg:backdrop-blur-none",
} as const;

/**
 * Action bar pinned to the bottom of detail screens on the phone (draft, onboarding, upgrade).
 * "solid": white with a hairline top; "fade": canvas fade. `desktop` picks the web layout.
 * Pages using it add bottom padding so content can scroll clear of it.
 */
export function BottomBar({
  children,
  variant = "solid",
  desktop,
}: {
  children: ReactNode;
  variant?: "solid" | "fade";
  desktop?: keyof typeof DESKTOP;
}) {
  return (
    <div
      className={cn(
        "fixed inset-x-0 bottom-0 z-10 mx-auto flex w-full max-w-[480px] flex-col gap-3 px-screen-x pt-4 pb-[calc(env(safe-area-inset-bottom)+24px)]",
        variant === "solid"
          ? "border-t border-line bg-surface/95 backdrop-blur"
          : "bg-[linear-gradient(180deg,transparent,var(--color-bg)_30%)]",
        desktop && DESKTOP[desktop],
      )}
    >
      {children}
    </div>
  );
}
