"use client";

import Link from "next/link";

import { Card } from "@/components/ui/Card";
import { useEntitlement } from "@/lib/api/hooks/billing";
import { copy } from "@/lib/copy/en";

const t = copy.settings;

export function PlanCard() {
  const ent = useEntitlement();
  const e = ent.data;
  if (!e) return null;
  const label =
    e.plan === "free"
      ? t.planFree(e.free_drafts_left ?? 0)
      : e.plan === "sprint"
        ? t.planSprint(e.days_left ?? 0)
        : t.planPro(e.days_left ?? 0);
  return (
    <Card>
      <h2 className="m-0 text-h2 font-semibold tracking-[-0.01em]">{t.planTitle}</h2>
      <p className="text-body">{label}</p>
      {e.plan === "free" && (
        <Link href="/upgrade" className="font-semibold">
          {t.upgrade}
        </Link>
      )}
    </Card>
  );
}
