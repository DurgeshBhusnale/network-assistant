"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { ImportPanel } from "@/components/people/ImportPanel";
import { BottomBar } from "@/components/ui/BottomBar";
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
      <div className="-mt-1">
        <h1 className="m-0 title">{copy.importFlow.title}</h1>
        <p className="m-0 mt-2 text-body leading-[22px] text-muted">{copy.importFlow.subtitle}</p>
      </div>
      <ImportPanel onAdded={(n) => setCount((c) => c + n)} />
      <BottomBar variant="fade">
        <Button
          size="lg"
          variant={count > 0 ? "primary" : "secondary"}
          fullWidth
          loading={update.isPending}
          onClick={next}
        >
          {count > 0 ? copy.importFlow.continueWith(count) : copy.common.skipForNow}
        </Button>
      </BottomBar>
    </>
  );
}
