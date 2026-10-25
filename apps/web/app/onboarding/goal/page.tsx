"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { ChipInput } from "@/components/ui/ChipInput";
import { cn } from "@/components/ui/cn";
import { FullScreenLoader } from "@/components/ui/FullScreenLoader";
import { Input } from "@/components/ui/Input";
import { ProgressSteps } from "@/components/ui/ProgressSteps";
import { Stepper } from "@/components/ui/Stepper";
import { ApiError } from "@/lib/api/client";
import { useCreateGoal, usePacks, type PackInfo } from "@/lib/api/hooks/account";
import { copy } from "@/lib/copy/en";

type Bounds = { min: number; max: number; default: number };

/** Referrals stepper bounds come from the pack's goal_schema, not hard-coded (ADR-0006). */
function targetBounds(pack: PackInfo | undefined): Bounds {
  const prop = (pack?.goal_schema?.properties as Record<string, Record<string, number>> | undefined)
    ?.referrals_target;
  return { min: prop?.minimum ?? 1, max: prop?.maximum ?? 10, default: prop?.default ?? 4 };
}

function splitList(value: string, separator: RegExp): string[] {
  return value
    .split(separator)
    .map((s) => s.trim())
    .filter(Boolean);
}

export default function GoalPage() {
  const packs = usePacks();
  const create = useCreateGoal();
  const router = useRouter();
  const t = copy.goal;

  const active = packs.data?.filter((p) => p.status === "active") ?? [];
  const [packId, setPackId] = useState<string | null>(null);
  const selected = packs.data?.find((p) => p.id === (packId ?? active[0]?.id));
  const bounds = targetBounds(selected);

  const [role, setRole] = useState("");
  const [companies, setCompanies] = useState<string[]>([]);
  const [target, setTarget] = useState<number | null>(null);
  const [where, setWhere] = useState("");
  const [showLinks, setShowLinks] = useState(false);
  const [links, setLinks] = useState("");
  const [error, setError] = useState<string | null>(null);

  if (packs.isPending) return <FullScreenLoader />;

  async function submit() {
    if (!selected) return;
    setError(null);
    try {
      await create.mutateAsync({
        pack_id: selected.id,
        params: {
          role,
          companies,
          referrals_target: target ?? bounds.default,
          locations: splitList(where, /,/),
          job_links: splitList(links, /\s+/),
        },
      });
      router.replace("/onboarding/import");
    } catch (e) {
      if (e instanceof ApiError && e.code === "GOAL_ALREADY_ACTIVE") {
        router.replace("/onboarding/import");
        return;
      }
      setError(e instanceof ApiError ? e.message : copy.common.genericError);
    }
  }

  return (
    <>
      <ProgressSteps step={1} />
      <h1 className="m-0 font-display text-h1 font-bold tracking-[-0.01em]">{t.title}</h1>

      <div className="grid grid-cols-2 gap-2.5">
        {packs.data?.map((pack) => {
          const isActive = pack.status === "active";
          const isSelected = pack.id === selected?.id;
          return (
            <button
              key={pack.id}
              type="button"
              disabled={!isActive}
              aria-pressed={isActive ? isSelected : undefined}
              onClick={() => setPackId(pack.id)}
              className={cn(
                "flex min-h-[72px] flex-col items-start gap-1 rounded-[12px] p-3 text-left",
                isSelected
                  ? "border-2 border-primary bg-primary-soft text-ink"
                  : "border border-line bg-surface text-muted",
                !isActive && "cursor-not-allowed",
              )}
            >
              <span className="text-[14px] font-semibold">{pack.picker_label}</span>
              <span className="text-caption">{isActive ? pack.name : copy.common.comingSoon}</span>
            </button>
          );
        })}
      </div>

      <div className="flex flex-col gap-4">
        <Input
          label={t.roleLabel}
          placeholder={t.rolePlaceholder}
          value={role}
          onChange={(e) => setRole(e.target.value)}
        />
        <ChipInput
          label={t.companiesLabel}
          values={companies}
          onChange={setCompanies}
          max={15}
          addLabel={t.addCompany}
          inputLabel={t.addCompanyLabel}
          removeLabel={t.removeChip}
          hint={t.companiesHint}
        />
        <div className="grid grid-cols-2 gap-3">
          <Stepper
            label={t.referralsLabel}
            value={target ?? bounds.default}
            min={bounds.min}
            max={bounds.max}
            onChange={setTarget}
          />
          <Input
            label={t.whereLabel}
            placeholder={t.wherePlaceholder}
            value={where}
            onChange={(e) => setWhere(e.target.value)}
          />
        </div>

        {showLinks ? (
          <div className="flex flex-col gap-1.5">
            <label htmlFor="job-links" className="text-small font-semibold">
              {t.jobLinksLabel}
            </label>
            <textarea
              id="job-links"
              rows={3}
              value={links}
              onChange={(e) => setLinks(e.target.value)}
              aria-describedby="job-links-hint"
              className="rounded-button border border-line-strong bg-surface p-3 text-body"
            />
            <p id="job-links-hint" className="text-caption text-muted">
              {t.jobLinksHint}
            </p>
          </div>
        ) : (
          <Button variant="ghost" className="self-start px-0" onClick={() => setShowLinks(true)}>
            {t.jobLinksToggle}
          </Button>
        )}
      </div>

      {error && (
        <p role="alert" className="text-small text-danger">
          {error}
        </p>
      )}
      <Button
        size="lg"
        fullWidth
        loading={create.isPending}
        disabled={!selected || role.trim().length < 2 || companies.length === 0}
        onClick={submit}
      >
        {copy.common.continue}
      </Button>
    </>
  );
}
