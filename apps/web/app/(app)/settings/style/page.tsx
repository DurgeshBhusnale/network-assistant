"use client";

import { StyleForm } from "@/components/drafts/StyleForm";
import { PageHeader } from "@/components/shell/PageHeader";
import { useStyle } from "@/lib/api/hooks/drafts";
import { copy } from "@/lib/copy/en";

export default function SettingsStylePage() {
  const style = useStyle();
  return (
    <>
      <PageHeader title={copy.settings.writingStyle} back="/settings" showSettings={false} />
      <div className="px-screen-x pt-5 lg:max-w-[816px] lg:pt-8">
        {style.isPending ? (
          <p role="status" className="text-small text-muted">
            {copy.common.loading}…
          </p>
        ) : (
          <StyleForm initial={style.data} />
        )}
      </div>
    </>
  );
}
