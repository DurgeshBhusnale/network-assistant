import Link from "next/link";

import { UserIcon } from "@/components/ui/icons";
import { copy } from "@/lib/copy/en";

export function PageHeader({ title, eyebrow }: { title: string; eyebrow?: string }) {
  return (
    <header className="flex items-start justify-between px-screen-x pt-6 pb-2">
      <div className="flex flex-col gap-0.5">
        {eyebrow && <span className="text-small text-muted">{eyebrow}</span>}
        <h1 className="m-0 font-display text-h1 font-bold tracking-[-0.01em]">{title}</h1>
      </div>
      <Link
        href="/settings"
        aria-label={copy.common.settings}
        className="inline-flex size-tap items-center justify-center rounded-pill border border-line bg-surface text-[14px] font-semibold text-ink no-underline"
      >
        <UserIcon />
      </Link>
    </header>
  );
}
