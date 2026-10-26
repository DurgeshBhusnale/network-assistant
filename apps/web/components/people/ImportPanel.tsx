"use client";

import Link from "next/link";
import { useRef, useState, useSyncExternalStore } from "react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ApiError } from "@/lib/api/client";
import {
  useCommitImport,
  useStageFile,
  useStagePicker,
  type ImportJob,
} from "@/lib/api/hooks/people";
import { copy } from "@/lib/copy/en";
import { contactPickerSupported, pickContacts } from "@/lib/device/contactPicker";

const t = copy.importFlow;
const REMIND_KEY = "linkedin-remind-later";

function subscribeNoop() {
  return () => {};
}

function readRemindLater(): boolean {
  try {
    return window.localStorage.getItem(REMIND_KEY) === "1";
  } catch {
    return false;
  }
}

/** Phone contacts (Contact Picker or .vcf), LinkedIn CSV, add by hand; preview then commit. */
export function ImportPanel({ onAdded }: { onAdded?: (count: number) => void }) {
  const pickerSupported = useSyncExternalStore(subscribeNoop, contactPickerSupported, () => false);
  const remindStored = useSyncExternalStore(subscribeNoop, readRemindLater, () => false);
  const [remindLater, setRemindLater] = useState(false);
  const stagePicker = useStagePicker();
  const stageFile = useStageFile();
  const commit = useCommitImport();
  const [preview, setPreview] = useState<ImportJob | null>(null);
  const [added, setAdded] = useState<Record<string, number>>({});
  const [error, setError] = useState<{ message: string; consent: boolean } | null>(null);
  const vcfInput = useRef<HTMLInputElement>(null);
  const csvInput = useRef<HTMLInputElement>(null);
  const busy = stagePicker.isPending || stageFile.isPending;

  function fail(e: unknown) {
    if (e instanceof ApiError) {
      setError({ message: e.message, consent: e.code === "CONSENT_REQUIRED" });
    } else {
      setError({ message: copy.common.genericError, consent: false });
    }
  }

  async function choosePhoneContacts() {
    setError(null);
    const picked = await pickContacts();
    if (picked.length === 0) return;
    try {
      setPreview(await stagePicker.mutateAsync(picked));
    } catch (e) {
      fail(e);
    }
  }

  async function upload(file: File | undefined) {
    if (!file) return;
    setError(null);
    try {
      setPreview(await stageFile.mutateAsync(file));
    } catch (e) {
      fail(e);
    }
  }

  async function confirm() {
    if (!preview) return;
    try {
      const done = await commit.mutateAsync(preview.id);
      setAdded((a) => ({ ...a, [done.source]: (a[done.source] ?? 0) + done.counts.new }));
      onAdded?.(done.counts.new);
      setPreview(null);
    } catch (e) {
      fail(e);
    }
  }

  function remind() {
    try {
      window.localStorage.setItem(REMIND_KEY, "1");
    } catch {
      // Storage unavailable: the card just stays visible.
    }
    setRemindLater(true);
  }

  const phoneAdded = (added.picker ?? 0) + (added.vcard ?? 0);
  const linkedinHidden = remindLater || (remindStored && !added.linkedin_csv);

  return (
    <div className="flex flex-col gap-gap-cards">
      <input
        ref={vcfInput}
        type="file"
        accept=".vcf,text/vcard,text/x-vcard"
        className="sr-only"
        tabIndex={-1}
        aria-hidden="true"
        onChange={(e) => {
          void upload(e.target.files?.[0]);
          e.target.value = "";
        }}
      />
      <input
        ref={csvInput}
        type="file"
        accept=".csv,text/csv"
        className="sr-only"
        tabIndex={-1}
        aria-hidden="true"
        onChange={(e) => {
          void upload(e.target.files?.[0]);
          e.target.value = "";
        }}
      />

      {preview ? (
        <Card aria-live="polite">
          <h2 className="m-0 font-display text-h2 font-semibold">{t.previewTitle}</h2>
          <p className="text-body">
            {t.previewCounts(preview.counts.new, preview.counts.merged, preview.counts.skipped)}
          </p>
          {preview.errors.length > 0 && (
            <details className="text-small text-ink-2">
              <summary className="min-h-tap cursor-pointer py-2 font-semibold">
                {t.skippedTitle} ({preview.counts.skipped})
              </summary>
              <ul className="m-0 flex flex-col gap-1 pl-4">
                {preview.errors.map((e) => (
                  <li key={e.row}>{t.skippedRow(e.row, e.reason)}</li>
                ))}
              </ul>
            </details>
          )}
          <div className="flex gap-2">
            <Button
              className="flex-1"
              loading={commit.isPending}
              disabled={preview.counts.new + preview.counts.merged === 0}
              onClick={confirm}
            >
              {t.confirm}
            </Button>
            <Button variant="secondary" onClick={() => setPreview(null)}>
              {t.cancel}
            </Button>
          </div>
          {preview.counts.new + preview.counts.merged === 0 && (
            <p className="text-small text-muted">{t.nothingNew}</p>
          )}
        </Card>
      ) : (
        <>
          <Card>
            <div className="flex items-center justify-between gap-2">
              <h2 className="m-0 text-body font-semibold">{t.phoneTitle}</h2>
              {phoneAdded > 0 && (
                <span className="text-small font-semibold text-success">{t.added(phoneAdded)}</span>
              )}
            </div>
            <p className="text-small text-muted">{pickerSupported ? t.phoneBody : t.vcardBody}</p>
            <Button
              variant="secondary"
              loading={busy}
              onClick={pickerSupported ? choosePhoneContacts : () => vcfInput.current?.click()}
            >
              {pickerSupported ? t.phoneButton : t.vcardButton}
            </Button>
          </Card>

          {!linkedinHidden ? (
            <Card>
              <div className="flex items-center justify-between gap-2">
                <h2 className="m-0 text-body font-semibold">{t.linkedinTitle}</h2>
                {added.linkedin_csv !== undefined && (
                  <span className="text-small font-semibold text-success">
                    {t.added(added.linkedin_csv)}
                  </span>
                )}
              </div>
              <p className="text-small text-muted">{t.linkedinBody}</p>
              <ol className="m-0 flex flex-col gap-1 pl-5 text-small text-ink-2">
                {t.linkedinSteps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
              <div className="flex gap-2">
                <Button
                  className="flex-1"
                  variant="secondary"
                  loading={busy}
                  onClick={() => csvInput.current?.click()}
                >
                  {t.uploadCsv}
                </Button>
                <Button variant="ghost" onClick={remind}>
                  {t.remindLater}
                </Button>
              </div>
            </Card>
          ) : (
            remindLater && <p className="text-small text-muted">{t.remindLaterDone}</p>
          )}

          <Link
            href="/people/new"
            className="flex min-h-tap flex-col gap-0.5 rounded-card border border-line bg-surface p-card text-ink no-underline"
          >
            <span className="text-body font-semibold">{t.manualTitle}</span>
            <span className="text-small text-muted">{t.manualBody}</span>
          </Link>
        </>
      )}

      {error && (
        <div role="alert" className="flex flex-col gap-1 text-small text-danger">
          <span>{error.consent ? t.consentNeeded : error.message}</span>
          {error.consent && (
            <Link href="/onboarding/consents" className="font-semibold">
              {t.consentLink}
            </Link>
          )}
        </div>
      )}
      <p className="text-caption text-muted">{t.privacy}</p>
    </div>
  );
}
