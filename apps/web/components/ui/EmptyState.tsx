import type { ReactNode } from "react";

export function EmptyState({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-start gap-2 rounded-card border border-line bg-surface p-card">
      <h2 className="font-display text-h2 font-semibold">{title}</h2>
      <p className="text-small text-muted">{body}</p>
      {action}
    </div>
  );
}
