import { useSyncExternalStore } from "react";

function subscribe(onChange: () => void) {
  const timer = window.setInterval(onChange, 60_000);
  return () => window.clearInterval(timer);
}

let cached = 0;
function snapshot(): number {
  // Minute resolution keeps the snapshot stable between renders.
  const minute = Math.floor(Date.now() / 60_000);
  if (minute !== cached) cached = minute;
  return cached;
}

/** The current time on the client only (null while prerendering), refreshed every minute. */
export function useNow(): Date | null {
  const minute = useSyncExternalStore(subscribe, snapshot, () => 0);
  return minute === 0 ? null : new Date(minute * 60_000);
}
