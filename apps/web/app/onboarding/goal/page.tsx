"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { BottomBar } from "@/components/ui/BottomBar";
import { Button } from "@/components/ui/Button";
import { ChipInput } from "@/components/ui/ChipInput";
import { cn } from "@/components/ui/cn";
import { FullScreenLoader } from "@/components/ui/FullScreenLoader";
import { CheckIcon } from "@/components/ui/icons";
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
      <div className="lg:max-w-[640px]">
        <ProgressSteps step={1} />
      </div>
      <h1 className="m-0 -mt-2 title">{t.title}</h1>

      <div className="grid grid-cols-2 gap-3 lg:max-w-[760px] lg:grid-cols-4">
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
                "flex h-24 flex-col justify-between rounded-tile p-4 text-left",
                isSelected
                  ? "bg-selected text-ink ring-selected"
                  : "bg-surface text-muted hairline",
                !isActive && "cursor-not-allowed",
              )}
            >
              <span className="flex w-full items-start justify-between gap-2">
                <span className="text-[16px] leading-5 font-semibold">{pack.picker_label}</span>
                {isSelected && (
                  <span
                    aria-hidden="true"
                    className="flex size-[22px] shrink-0 items-center justify-center rounded-pill bg-grad text-on-primary"
                  >
                    <CheckIcon size={13} strokeWidth={3} />
                  </span>
                )}
              </span>
              <span className={cn("text-caption", isActive ? "text-ink-2" : "font-semibold")}>
                {isActive ? pack.name : copy.common.comingSoon}
              </span>
            </button>
          );
        })}
      </div>

      <div className="flex flex-col gap-5 lg:grid lg:max-w-[760px] lg:grid-cols-2 lg:items-start lg:gap-x-5 lg:gap-y-6">
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

        {showLinks ? (
          <div className="flex flex-col gap-2 lg:col-span-2">
            <label htmlFor="job-links" className="text-small font-semibold">
              {t.jobLinksLabel}
            </label>
            <textarea
              id="job-links"
              rows={3}
              value={links}
              onChange={(e) => setLinks(e.target.value)}
              aria-describedby="job-links-hint"
              className="rounded-button bg-surface p-4 text-[16px] hairline-strong focus:shadow-[inset_0_0_0_1.5px_var(--color-primary-ring)] focus:outline-none"
            />
            <p id="job-links-hint" className="text-caption text-muted">
              {t.jobLinksHint}
            </p>
          </div>
        ) : (
          <Button
            variant="ghost"
            className="self-start lg:col-span-2 lg:justify-self-start"
            onClick={() => setShowLinks(true)}
          >
            {t.jobLinksToggle}
          </Button>
        )}
      </div>

      {error && (
        <p role="alert" className="m-0 text-small text-danger">
          {error}
        </p>
      )}
      <BottomBar variant="fade" desktop="footer">
        <Button
          size="lg"
          fullWidth
          loading={create.isPending}
          disabled={!selected || role.trim().length < 2 || companies.length === 0}
          onClick={submit}
        >
          {copy.common.continue}
        </Button>
      </BottomBar>
    </>
  );
}
