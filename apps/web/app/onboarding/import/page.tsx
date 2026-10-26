"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { ImportPanel } from "@/components/people/ImportPanel";
import { Button } from "@/components/ui/Button";
import { ProgressSteps } from "@/components/ui/ProgressSteps";
import { useUpdateMe } from "@/lib/api/hooks/account";
import { copy } from "@/lib/copy/en";

export default function ImportStepPage() {
  const update = useUpdateMe();
  const router = useRouter();
  const [count, setCount] = useState(0);

  async function next() {
    await update.mutateAsync({ onboarding_step: "style" });
    router.replace("/onboarding/style");
  }

  return (
    <>
      <ProgressSteps step={2} />
      <h1 className="m-0 font-display text-h1 font-bold tracking-[-0.01em]">
        {copy.importFlow.title}
      </h1>
      <ImportPanel onAdded={(n) => setCount((c) => c + n)} />
      <Button size="lg" fullWidth loading={update.isPending} onClick={next}>
        {count > 0 ? copy.importFlow.continueWith(count) : copy.common.skipForNow}
      </Button>
    </>
  );
}
