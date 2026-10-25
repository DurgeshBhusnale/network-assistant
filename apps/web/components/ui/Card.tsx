import type { HTMLAttributes } from "react";

import { cn } from "./cn";

export function Card({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "flex flex-col gap-2.5 rounded-card border border-line bg-surface p-card",
        className,
      )}
      {...rest}
    />
  );
}
