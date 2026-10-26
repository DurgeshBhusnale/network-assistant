import type { HTMLAttributes } from "react";

import { cn } from "./cn";

/** White card, 24 px radius, hairline + soft lift (v4). */
export function Card({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("flex flex-col gap-4 rounded-card bg-surface p-card shadow-card", className)}
      {...rest}
    />
  );
}
