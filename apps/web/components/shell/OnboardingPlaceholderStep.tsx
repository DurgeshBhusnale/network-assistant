"use client";

import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { ProgressSteps } from "@/components/ui/ProgressSteps";
import { useUpdateMe, type Profile } from "@/lib/api/hooks/account";
import { copy } from "@/lib/copy/en";

/** Onboarding steps 2–3 until their sprints land: explain, then let the user skip (FR-ONB-1). */
export function OnboardingPlaceholderStep({
  step,
  title,
  body,
  next,
  nextRoute,
}: {
  step: number;
  title: string;
  body: string;
  next: Profile["onboarding_step"];
  nextRoute: string;
}) {
  const update = useUpdateMe();
  const router = useRouter();

  async function skip() {
    await update.mutateAsync({ onboarding_step: next });
    router.replace(nextRoute);
  }

  return (
    <>
      <ProgressSteps step={step} />
      <h1 className="m-0 title">{title}</h1>
      <p className="text-body text-ink-2">{body}</p>
      {update.isError && (
        <p role="alert" className="text-small text-danger">
          {copy.common.genericError}
        </p>
      )}
      <Button size="lg" fullWidth loading={update.isPending} onClick={skip}>
        {copy.common.skipForNow}
      </Button>
    </>
  );
}
