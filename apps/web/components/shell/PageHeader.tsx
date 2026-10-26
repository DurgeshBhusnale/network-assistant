import Link from "next/link";
import type { ReactNode } from "react";

import { BackIcon, UserIcon } from "@/components/ui/icons";
import { copy } from "@/lib/copy/en";

/**
 * Screen header (v4): optional muted eyebrow, a 32 px display title, and on the right either a
 * short meta line ("286 contacts") or the round Settings button. `back` shows a round back link.
 */
export function PageHeader({
  title,
  eyebrow,
  meta,
  back,
  showSettings = true,
  children,
}: {
  title: string;
  eyebrow?: string;
  meta?: ReactNode;
  back?: string;
  showSettings?: boolean;
  children?: ReactNode;
}) {
  return (
    <header className="flex flex-col gap-2 px-screen-x pt-6 pb-1 lg:pt-10">
      {back && (
        <Link
          href={back}
          aria-label={copy.common.back}
          className="mb-2 inline-flex size-tap items-center justify-center rounded-pill text-ink hairline-strong hover:text-ink"
        >
          <BackIcon />
        </Link>
      )}
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 flex-col gap-0.5">
          {eyebrow && <span className="text-small text-muted">{eyebrow}</span>}
          <h1 className="m-0 title-lg">{title}</h1>
        </div>
        {meta !== undefined ? (
          <span className="shrink-0 pt-3 text-small text-muted">{meta}</span>
        ) : (
          showSettings && (
            <Link
              href="/settings"
              aria-label={copy.common.settings}
              className="inline-flex size-tap shrink-0 items-center justify-center rounded-pill bg-primary-soft text-primary no-underline"
            >
              <UserIcon size={20} />
            </Link>
          )
        )}
      </div>
      {children}
    </header>
  );
}
