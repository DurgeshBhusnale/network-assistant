"use client";

import { useRouter } from "next/navigation";

import { StyleForm } from "@/components/drafts/StyleForm";
import { Button } from "@/components/ui/Button";
import { FullScreenLoader } from "@/components/ui/FullScreenLoader";
import { ProgressSteps } from "@/components/ui/ProgressSteps";
import { useUpdateMe } from "@/lib/api/hooks/account";
import { useStyle } from "@/lib/api/hooks/drafts";
import { copy } from "@/lib/copy/en";

export default function StyleStepPage() {
  const style = useStyle();
  const update = useUpdateMe();
  const router = useRouter();

  async function finish() {
    await update.mutateAsync({ onboarding_step: "done" });
    router.replace("/today");
  }

  if (style.isPending) return <FullScreenLoader />;
  return (
    <>
      <div className="lg:max-w-[640px]">
        <ProgressSteps step={3} />
      </div>
      <h1 className="m-0 -mt-2 title">{copy.style.title}</h1>
      <StyleForm initial={style.data} onSaved={() => void finish()} />
      <Button
        variant="ghost"
        className="self-center"
        loading={update.isPending}
        onClick={() => void finish()}
      >
        {copy.common.skipForNow}
      </Button>
    </>
  );
}
