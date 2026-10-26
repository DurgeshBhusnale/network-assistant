import type { ReactNode } from "react";

import { cn } from "./cn";

/** Uppercase section label: 12 px / 700 / 0.08em, muted (or accent). */
export function SectionLabel({
  children,
  tone = "muted",
  className,
  as: Tag = "h2",
}: {
  children: ReactNode;
  tone?: "muted" | "accent" | "info";
  className?: string;
  as?: "h2" | "h3" | "p" | "span";
}) {
  return (
    <Tag
      className={cn(
        "m-0 label-caps",
        tone === "muted" && "text-muted",
        tone === "accent" && "text-primary",
        tone === "info" && "text-info-text",
        className,
      )}
    >
      {children}
    </Tag>
  );
}
