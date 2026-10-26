"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { ConsentsForm } from "@/components/privacy/ConsentsForm";
import { PageHeader } from "@/components/shell/PageHeader";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { ApiError } from "@/lib/api/client";
import { useConsents, useDeleteAccount, useExportData } from "@/lib/api/hooks/account";
import { signOut } from "@/lib/auth/AuthProvider";
import { copy } from "@/lib/copy/en";

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function errorText(e: unknown): string {
  return e instanceof ApiError ? e.message : copy.common.genericError;
}

export default function PrivacySettingsPage() {
  const consents = useConsents();
  const t = copy.privacyPage;
  const [saved, setSaved] = useState(false);

  return (
    <>
      <PageHeader title={t.title} back="/settings" showSettings={false} />
      <div className="flex flex-col gap-gap-cards px-screen-x pt-5 lg:max-w-[816px] lg:pt-8">
        {consents.isPending ? (
          <p role="status" className="text-small text-muted">
            {copy.common.loading}…
          </p>
        ) : (
          <Card>
            <ConsentsForm
              initial={consents.data}
              submitLabel={copy.settings.save}
              onSaved={() => setSaved(true)}
            />
            {saved && (
              <p role="status" className="text-small text-muted">
                {t.choicesSaved}
              </p>
            )}
          </Card>
        )}
        <ExportCard />
        <DeleteCard />
      </div>
    </>
  );
}

function ExportCard() {
  const exportData = useExportData();
  const t = copy.privacyPage;

  async function download() {
    const { blob, filename } = await exportData.mutateAsync();
    saveBlob(blob, filename);
  }

  return (
    <Card>
      <h2 className="m-0 text-h2 font-semibold tracking-[-0.01em]">{t.exportTitle}</h2>
      <p className="text-small text-ink-2">{t.exportBody}</p>
      <Button
        variant="secondary"
        loading={exportData.isPending}
        onClick={() => void download().catch(() => {})}
      >
        {t.exportButton}
      </Button>
      {exportData.error && (
        <p role="alert" className="text-small text-danger">
          {errorText(exportData.error)}
        </p>
      )}
    </Card>
  );
}

function DeleteCard() {
  const remove = useDeleteAccount();
  const router = useRouter();
  const t = copy.privacyPage;
  const [confirm, setConfirm] = useState("");

  async function deleteAccount() {
    await remove.mutateAsync(confirm);
    await signOut();
    router.replace("/sign-in");
  }

  return (
    <Card>
      <h2 className="m-0 text-h2 font-semibold tracking-[-0.01em]">{t.deleteTitle}</h2>
      <p className="text-small text-ink-2">{t.deleteBody}</p>
      <Input
        label={t.deleteLabel}
        autoComplete="off"
        autoCapitalize="characters"
        value={confirm}
        onChange={(e) => setConfirm(e.target.value)}
      />
      <Button
        variant="secondary"
        className="border-danger text-danger"
        loading={remove.isPending}
        disabled={confirm.trim().toUpperCase() !== "DELETE"}
        onClick={() => void deleteAccount().catch(() => {})}
      >
        {t.deleteButton}
      </Button>
      {remove.error && (
        <p role="alert" className="text-small text-danger">
          {errorText(remove.error)}
        </p>
      )}
    </Card>
  );
}
