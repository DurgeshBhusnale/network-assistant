"use client";

import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { useHealth } from "@/lib/api/hooks/useHealth";
import { copy } from "@/lib/copy/en";

/** Sprint 0: shows the shell talking to the API, database and Redis. Removed when Today lands. */
export function SystemStatus() {
  const health = useHealth();
  const s = copy.status;

  return (
    <Card aria-live="polite" data-testid="system-status">
      <h2 className="font-display text-h2 font-semibold">{s.title}</h2>
      {health.isPending && <p className="text-small text-muted">{s.checking}</p>}
      {health.isError && <p className="text-small text-danger">{s.unreachable}</p>}
      {health.data && (
        <div className="flex flex-wrap gap-1.5">
          <Chip tone={health.data.status === "ok" ? "neutral" : "highlight"}>
            {s.api}: {health.data.status}
          </Chip>
          <Chip tone={health.data.db === "ok" ? "neutral" : "highlight"}>
            {s.db}: {health.data.db === "ok" ? s.ok : s.down}
          </Chip>
          <Chip tone={health.data.redis === "ok" ? "neutral" : "highlight"}>
            {s.redis}: {health.data.redis === "ok" ? s.ok : s.down}
          </Chip>
        </div>
      )}
    </Card>
  );
}
