import type { ComponentType, ReactNode } from "react";

/** Centred empty state (v4): tinted icon disc, display title, short body, then actions. */
export function EmptyState({
  title,
  body,
  action,
  Icon,
}: {
  title: string;
  body: string;
  action?: ReactNode;
  Icon?: ComponentType<{ size?: number }>;
}) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 px-2 py-10 text-center">
      {Icon && (
        <span
          aria-hidden="true"
          className="mb-3 flex size-[104px] items-center justify-center rounded-pill bg-primary-soft text-primary"
        >
          <Icon size={40} />
        </span>
      )}
      <h2 className="m-0 font-display text-[24px] leading-[30px] font-semibold tracking-[-0.02em]">
        {title}
      </h2>
      <p className="m-0 max-w-[280px] text-body leading-[23px] text-muted">{body}</p>
      {action && <div className="mt-3 flex flex-col items-center gap-1">{action}</div>}
    </div>
  );
}
