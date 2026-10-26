"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { cn } from "@/components/ui/cn";
import { CheckIcon } from "@/components/ui/icons";
import { copy } from "@/lib/copy/en";

const STEPS = ["/onboarding/goal", "/onboarding/import", "/onboarding/style"];

/** Onboarding frame: phone column; on desktop an indigo panel with the steps (web design). */
export function OnboardingFrame({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const current = STEPS.indexOf(pathname); // -1 on the consents screen
  const t = copy.onboarding;

  return (
    <div className="lg:flex lg:min-h-dvh">
      <aside className="hidden w-[480px] shrink-0 flex-col bg-hero p-12 text-on-dark lg:sticky lg:top-0 lg:flex lg:h-dvh">
        <div className="flex items-center gap-3">
          <span aria-hidden="true" className="size-8 rounded-[10px] bg-grad-soft-bar" />
          <span className="font-display text-[20px] font-semibold">{copy.appName}</span>
        </div>
        <p className="m-0 mt-20 font-display text-[40px] leading-[46px] font-semibold tracking-[-0.025em]">
          {t.panelTitle}
        </p>
        <ol className="m-0 mt-14 flex list-none flex-col gap-5 p-0">
          {t.panelSteps.map((label, i) => {
            const done = current > i;
            const on = current === i;
            return (
              <li
                key={label}
                aria-current={on ? "step" : undefined}
                className={cn(
                  "flex items-center gap-3.5 text-[16px] font-semibold",
                  on || done ? "text-on-dark" : "text-on-dark-muted/70",
                )}
              >
                <span
                  aria-hidden="true"
                  className={cn(
                    "flex size-8 items-center justify-center rounded-pill text-small",
                    on && "bg-surface text-hero-to",
                    done && "bg-on-dark/20",
                    !on && !done && "bg-on-dark/10",
                  )}
                >
                  {done ? <CheckIcon size={16} strokeWidth={2.5} /> : i + 1}
                </span>
                {label}
              </li>
            );
          })}
        </ol>
      </aside>
      <main className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col gap-section px-screen-x pt-6 pb-[150px] lg:mx-0 lg:max-w-[904px] lg:flex-1 lg:px-[72px] lg:pt-14 lg:pb-[140px]">
        {children}
      </main>
    </div>
  );
}
