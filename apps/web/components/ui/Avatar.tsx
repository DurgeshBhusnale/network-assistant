import { cn } from "./cn";

const tints = [
  "bg-primary-soft text-primary",
  "bg-accent-soft text-accent-text",
  "bg-success-soft text-success",
] as const;

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  const letters = parts.length > 1 ? [parts[0], parts[parts.length - 1]] : parts.slice(0, 1);
  return letters.map((p) => (p ?? "").charAt(0).toUpperCase()).join("") || "?";
}

export function tintIndex(name: string): number {
  let hash = 0;
  for (const ch of name) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0;
  return hash % tints.length;
}

const sizes = {
  md: "size-10 text-[14px]",
  lg: "size-[72px] text-[24px] font-display",
} as const;

/** Initials avatar tinted by a stable hash of the name. Decorative next to a visible name. */
export function Avatar({ name, size = "md" }: { name: string; size?: keyof typeof sizes }) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-pill font-semibold",
        tints[tintIndex(name)],
        sizes[size],
      )}
    >
      {initials(name)}
    </span>
  );
}
