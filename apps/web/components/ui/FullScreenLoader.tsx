import { copy } from "@/lib/copy/en";

export function FullScreenLoader({ label = copy.common.loading }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="flex min-h-dvh items-center justify-center">
      <span
        aria-hidden="true"
        className="size-8 animate-spin rounded-pill border-[3px] border-primary border-t-transparent"
      />
      <span className="sr-only">{label}</span>
    </div>
  );
}
