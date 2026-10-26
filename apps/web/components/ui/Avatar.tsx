import type { CSSProperties } from "react";

import { cn } from "./cn";

const TINTS = 6; // --avatar-1 … --avatar-6 in design/tokens.css

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  const letters = parts.length > 1 ? [parts[0], parts[parts.length - 1]] : parts.slice(0, 1);
  return letters.map((p) => (p ?? "").charAt(0).toUpperCase()).join("") || "?";
}

export function tintIndex(name: string): number {
  let hash = 0;
  for (const ch of name) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0;
  return hash % TINTS;
}

const sizes = {
  sm: "size-10 text-[14px]",
  md: "size-11 text-[15px]",
  lg: "size-12 text-[17px]",
  xl: "size-14 text-[19px]",
  hero: "size-24 text-[32px] shadow-[0_0_0_6px_var(--color-surface),0_0_0_7px_var(--color-line)]",
} as const;

export type AvatarSize = keyof typeof sizes;

/** Initials avatar tinted by a stable hash of the name. Decorative next to a visible name. */
export function Avatar({ name, size = "lg" }: { name: string; size?: AvatarSize }) {
  const n = tintIndex(name) + 1;
  const style: CSSProperties = {
    backgroundColor: `var(--avatar-${n}-bg)`,
    color: `var(--avatar-${n}-fg)`,
  };
  return (
    <span
      aria-hidden="true"
      style={style}
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-pill font-semibold",
        sizes[size],
      )}
    >
      {initials(name)}
    </span>
  );
}
