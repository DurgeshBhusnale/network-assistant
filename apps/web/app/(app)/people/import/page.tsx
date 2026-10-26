"use client";

import { PageHeader } from "@/components/shell/PageHeader";
import { ImportPanel } from "@/components/people/ImportPanel";
import { copy } from "@/lib/copy/en";

export default function ImportPeoplePage() {
  return (
    <>
      <PageHeader title={copy.people.import} />
      <div className="px-screen-x pt-2">
        <ImportPanel />
      </div>
    </>
  );
}
