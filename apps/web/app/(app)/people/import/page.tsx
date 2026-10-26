"use client";

import { PageHeader } from "@/components/shell/PageHeader";
import { ImportPanel } from "@/components/people/ImportPanel";
import { copy } from "@/lib/copy/en";

export default function ImportPeoplePage() {
  return (
    <>
      <PageHeader title={copy.importFlow.title} back="/people" showSettings={false} />
      <div className="flex flex-col gap-5 px-screen-x pt-3 lg:pt-6">
        <p className="m-0 text-body leading-[22px] text-muted">{copy.importFlow.subtitle}</p>
        <ImportPanel />
      </div>
    </>
  );
}
