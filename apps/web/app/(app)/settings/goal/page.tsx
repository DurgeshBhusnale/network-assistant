"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { PageHeader } from "@/components/shell/PageHeader";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ChipInput } from "@/components/ui/ChipInput";
import { Input } from "@/components/ui/Input";
import { Stepper } from "@/components/ui/Stepper";
import { ApiError } from "@/lib/api/client";
import {
  useCurrentGoal,
  usePacks,
  useUpdateGoal,
  type Goal,
  type PackInfo,
} from "@/lib/api/hooks/account";
import { copy } from "@/lib/copy/en";

type Bounds = { min: number; max: number };

function targetBounds(pack: PackInfo | undefined): Bounds {
  const prop = (pack?.goal_schema?.properties as Record<string, Record<string, number>> | undefined)
    ?.referrals_target;
  return { min: prop?.minimum ?? 1, max: prop?.maximum ?? 10 };
}

function splitList(value: string, separator: RegExp): string[] {
  return value
    .split(separator)
    .map((s) => s.trim())
    .filter(Boolean);
}

function strings(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((v): v is string => typeof v === "string") : [];
}

export default function GoalSettingsPage() {
  const goal = useCurrentGoal();
  const t = copy.goalSettings;
  return (
    <>
      <PageHeader title={t.title} eyebrow={copy.settings.title} />
      <div className="flex flex-col gap-gap-cards px-screen-x pt-2">
        {goal.isPending ? (
          <p role="status" className="text-small text-muted">
            {copy.common.loading}…
          </p>
        ) : goal.data ? (
          <GoalForm key={`${goal.data.id}-${goal.data.status}`} goal={goal.data} />
        ) : (
          <Card>
            <p className="text-body text-ink-2">{t.none}</p>
            <Link
              href="/onboarding/goal"
              className="inline-flex min-h-tap items-center justify-center rounded-button bg-primary px-4 text-[14px] font-semibold text-on-primary no-underline"
            >
              {t.start}
            </Link>
          </Card>
        )}
      </div>
    </>
  );
}

function GoalForm({ goal }: { goal: Goal }) {
  const packs = usePacks();
  const update = useUpdateGoal();
  const router = useRouter();
  const t = copy.goalSettings;
  const g = copy.goal;
  const bounds = targetBounds(packs.data?.find((p) => p.id === goal.pack_id));

  const p = goal.params;
  const [role, setRole] = useState(typeof p.role === "string" ? p.role : "");
  const [companies, setCompanies] = useState(strings(p.companies));
  const [target, setTarget] = useState(
    typeof p.referrals_target === "number" ? p.referrals_target : bounds.min,
  );
  const [where, setWhere] = useState(strings(p.locations).join(", "));
  const [links, setLinks] = useState(strings(p.job_links).join("\n"));
  const [confirmEnd, setConfirmEnd] = useState(false);
  const [message, setMessage] = useState<{ text: string; error: boolean } | null>(null);

  async function run(body: Parameters<typeof update.mutateAsync>[0]["body"], done?: string) {
    setMessage(null);
    try {
      await update.mutateAsync({ id: goal.id, body });
      if (done) setMessage({ text: done, error: false });
      return true;
    } catch (e) {
      setMessage({
        text: e instanceof ApiError ? e.message : copy.common.genericError,
        error: true,
      });
      return false;
    }
  }

  function save() {
    void run(
      {
        params: {
          ...p,
          role,
          companies,
          referrals_target: target,
          locations: splitList(where, /,/),
          job_links: splitList(links, /\s+/),
        },
      },
      t.saved,
    );
  }

  async function end() {
    if (await run({ status: "done" })) router.replace("/onboarding/goal");
  }

  const paused = goal.status === "paused";

  return (
    <>
      <Card>
        <p className="text-small text-muted">
          {paused ? t.paused : t.dayOf(goal.day_number, goal.days_left)}
        </p>
        <Input label={g.roleLabel} value={role} onChange={(e) => setRole(e.target.value)} />
        <ChipInput
          label={g.companiesLabel}
          values={companies}
          onChange={setCompanies}
          max={15}
          addLabel={g.addCompany}
          inputLabel={g.addCompanyLabel}
          removeLabel={g.removeChip}
          hint={g.companiesHint}
        />
        <div className="grid grid-cols-2 gap-3">
          <Stepper
            label={g.referralsLabel}
            value={target}
            min={bounds.min}
            max={bounds.max}
            onChange={setTarget}
          />
          <Input label={g.whereLabel} value={where} onChange={(e) => setWhere(e.target.value)} />
        </div>
        <div className="flex flex-col gap-1.5">
          <label htmlFor="goal-job-links" className="text-small font-semibold">
            {g.jobLinksLabel}
          </label>
          <textarea
            id="goal-job-links"
            rows={3}
            value={links}
            onChange={(e) => setLinks(e.target.value)}
            className="rounded-button border border-line-strong bg-surface p-3 text-body"
          />
        </div>
        <Button
          loading={update.isPending}
          disabled={role.trim().length < 2 || companies.length === 0}
          onClick={save}
        >
          {t.save}
        </Button>
        {message && (
          <p
            role={message.error ? "alert" : "status"}
            className={message.error ? "text-small text-danger" : "text-small text-muted"}
          >
            {message.text}
          </p>
        )}
      </Card>

      <Card>
        <Button
          variant="secondary"
          disabled={update.isPending}
          onClick={() => void run({ status: paused ? "active" : "paused" })}
        >
          {paused ? t.resume : t.pause}
        </Button>
        {confirmEnd ? (
          <>
            <p className="text-small text-ink-2">{t.endConfirm}</p>
            <Button
              variant="secondary"
              className="border-danger text-danger"
              loading={update.isPending}
              onClick={() => void end()}
            >
              {t.endYes}
            </Button>
          </>
        ) : (
          <Button variant="ghost" onClick={() => setConfirmEnd(true)}>
            {t.end}
          </Button>
        )}
      </Card>
    </>
  );
}
