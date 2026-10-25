"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";

import { ConfirmCard, initialChoice, type CardChoice } from "@/components/capture/ConfirmCard";
import { Button } from "@/components/ui/Button";
import { MicIcon } from "@/components/ui/icons";
import { ApiError } from "@/lib/api/client";
import {
  useCapture,
  useConfirmCapture,
  useCreateCapture,
  useDiscardCapture,
  useUploadAudio,
  type Capture,
  type UploadMime,
} from "@/lib/api/hooks/captures";
import { usePerson } from "@/lib/api/hooks/people";
import { copy } from "@/lib/copy/en";
import {
  baseMime,
  recordingSupported,
  startRecording,
  type RecorderHandle,
} from "@/lib/device/recorder";

const t = copy.capture;
const BARS = 32;

function noopSubscribe() {
  return () => {};
}

function readContactParam(): string | null {
  return new URLSearchParams(window.location.search).get("contact");
}

function formatTime(ms: number): string {
  const s = Math.floor(ms / 1000);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

function Recorder({
  contactName,
  onCapture,
  busy,
}: {
  contactName: string | null;
  onCapture: (input: { blob?: Blob; mime?: string; text?: string }) => void;
  busy: boolean;
}) {
  const supported = useSyncExternalStore(noopSubscribe, recordingSupported, () => true);
  const [mode, setMode] = useState<"voice" | "text">("voice");
  const [recording, setRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [levels, setLevels] = useState<number[]>(() => Array(BARS).fill(0.05));
  const [error, setError] = useState<string | null>(null);
  const [text, setText] = useState("");
  const handle = useRef<RecorderHandle | null>(null);
  const started = useRef(0);
  const frame = useRef(0);

  useEffect(() => () => handle.current?.cancel(), []);

  function tick() {
    const h = handle.current;
    if (!h) return;
    setElapsed(Date.now() - started.current);
    setLevels((prev) => [...prev.slice(1), Math.max(0.05, h.level() * 2.2)]);
    frame.current = window.requestAnimationFrame(tick);
  }

  async function stop(limitHit = false) {
    const h = handle.current;
    if (!h) return;
    window.cancelAnimationFrame(frame.current);
    handle.current = null;
    setRecording(false);
    if (limitHit) setError(t.limit);
    const blob = await h.stop();
    onCapture({ blob, mime: h.mime });
  }

  async function start() {
    setError(null);
    try {
      handle.current = await startRecording(() => void stop(true));
      started.current = Date.now();
      setRecording(true);
      frame.current = window.requestAnimationFrame(tick);
    } catch {
      setError(t.micDenied);
    }
  }

  const voice = supported && mode === "voice";
  return (
    <section className="flex flex-col gap-4 rounded-panel bg-surface-dark p-4 text-on-dark">
      <p className="m-0 text-center text-body">
        {contactName ? t.promptPerson(contactName) : t.prompt}
      </p>
      {voice ? (
        <>
          <div className="flex h-12 items-center justify-center gap-[3px]" aria-hidden="true">
            {levels.map((l, i) => (
              <span
                key={i}
                className={
                  recording ? "w-1 rounded-[2px] bg-accent" : "w-1 rounded-[2px] bg-waveform-idle"
                }
                style={{ height: `${Math.round(Math.min(1, l) * 48)}px` }}
              />
            ))}
          </div>
          <span className="text-center font-display text-[28px] font-bold" aria-live="off">
            {formatTime(elapsed)}
          </span>
          <button
            type="button"
            aria-label={recording ? t.stop : t.start}
            disabled={busy}
            onClick={() => void (recording ? stop() : start())}
            className="mx-auto flex size-[72px] items-center justify-center rounded-pill bg-accent text-on-accent disabled:opacity-50"
          >
            {recording ? (
              <span className="size-6 rounded-[4px] bg-on-accent" aria-hidden="true" />
            ) : (
              <MicIcon size={30} />
            )}
          </button>
        </>
      ) : (
        <div className="flex flex-col gap-2">
          {!supported && <p className="text-small text-on-dark-soft">{t.unsupported}</p>}
          <label htmlFor="capture-text" className="text-small font-semibold">
            {t.textLabel}
          </label>
          <textarea
            id="capture-text"
            rows={5}
            maxLength={4000}
            value={text}
            placeholder={t.textPlaceholder}
            onChange={(e) => setText(e.target.value)}
            className="rounded-button border-0 bg-surface p-3 text-body text-ink"
          />
          <Button
            variant="accent"
            size="lg"
            fullWidth
            loading={busy}
            disabled={text.trim().length < 3}
            onClick={() => onCapture({ text: text.trim() })}
          >
            {t.process}
          </Button>
        </div>
      )}
      {supported && !recording && (
        <button
          type="button"
          onClick={() => setMode(mode === "voice" ? "text" : "voice")}
          className="min-h-tap self-center text-small font-semibold text-on-dark underline"
        >
          {mode === "voice" ? t.typeInstead : t.recordInstead}
        </button>
      )}
      {error && (
        <p role="alert" className="m-0 text-center text-small text-on-dark-soft">
          {error}
        </p>
      )}
    </section>
  );
}

function Results({ capture, onReset }: { capture: Capture; onReset: () => void }) {
  const confirm = useConfirmCapture(capture.id);
  const discard = useDiscardCapture(capture.id);
  const forContact = capture.for_contact_id !== null;
  const [choices, setChoices] = useState<Record<string, CardChoice>>(() =>
    Object.fromEntries(capture.people.map((p) => [p.key, initialChoice(p, forContact)])),
  );
  const [result, setResult] = useState<{ people: number; followUps: number } | null>(null);

  async function save() {
    const decisions = capture.people.map((p) => {
      const c = choices[p.key] ?? initialChoice(p, forContact);
      return {
        key: p.key,
        action: c.action,
        contact_id: c.action === "merge" ? (c.contactId ?? null) : null,
        full_name: c.action === "new" ? c.fullName.trim() || p.full_name : null,
        company: c.action === "new" ? c.company.trim() || null : null,
      };
    });
    const r = await confirm.mutateAsync(decisions);
    setResult({ people: r.created + r.merged, followUps: r.follow_ups });
  }

  if (result) {
    return (
      <div className="flex flex-col gap-3" role="status">
        <p className="text-body font-semibold">{t.saved(result.people, result.followUps)}</p>
        <Button variant="secondary" onClick={onReset}>
          {t.another}
        </Button>
        <Link href="/today" className="font-semibold">
          {copy.nav.today}
        </Link>
      </div>
    );
  }

  if (capture.people.length === 0) {
    return (
      <div className="flex flex-col gap-3">
        <p className="text-body">{t.noneFound}</p>
        <Button variant="secondary" onClick={onReset}>
          {t.another}
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-gap-cards">
      <h2 className="m-0 font-display text-h2 font-semibold">{t.found(capture.people.length)}</h2>
      {capture.people.map((p) => (
        <ConfirmCard
          key={p.key}
          candidate={p}
          forContact={forContact}
          choice={choices[p.key] ?? initialChoice(p, forContact)}
          onChange={(c) => setChoices((all) => ({ ...all, [p.key]: c }))}
        />
      ))}
      {confirm.error && (
        <p role="alert" className="text-small text-danger">
          {confirm.error instanceof ApiError ? confirm.error.message : copy.common.genericError}
        </p>
      )}
      <Button size="lg" fullWidth loading={confirm.isPending} onClick={() => void save()}>
        {t.saveAll}
      </Button>
      <Button
        variant="ghost"
        loading={discard.isPending}
        onClick={() => void discard.mutateAsync().then(onReset)}
      >
        {t.discardAll}
      </Button>
    </div>
  );
}

export default function CapturePage() {
  const router = useRouter();
  const contactId = useSyncExternalStore(noopSubscribe, readContactParam, () => null);
  const person = usePerson(contactId ?? "");
  const upload = useUploadAudio();
  const create = useCreateCapture();
  const [captureId, setCaptureId] = useState<string | null>(null);
  const capture = useCapture(captureId);
  const [error, setError] = useState<string | null>(null);
  const contactName = contactId && person.data ? person.data.full_name : null;

  async function onCapture(input: { blob?: Blob; mime?: string; text?: string }) {
    setError(null);
    try {
      let storagePath: string | undefined;
      if (input.blob) {
        storagePath = await upload.mutateAsync({
          blob: input.blob,
          mime: baseMime(input.mime ?? "audio/webm") as UploadMime,
        });
      }
      const c = await create.mutateAsync({
        text: input.text ?? null,
        storage_path: storagePath ?? null,
        contact_id: contactId,
      });
      setCaptureId(c.id);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : copy.common.genericError);
    }
  }

  const status = capture.data?.status;
  const working =
    upload.isPending || create.isPending || status === "queued" || status === "processing";
  const failed = status === "failed" ? capture.data?.error : null;

  return (
    <div className="flex flex-col gap-gap-cards px-screen-x pt-4">
      <button
        type="button"
        aria-label={t.close}
        onClick={() => router.back()}
        className="inline-flex size-tap items-center justify-center self-end rounded-pill border border-line bg-surface text-[18px]"
      >
        ×
      </button>

      {status !== "ready" && (
        <Recorder contactName={contactName} onCapture={(i) => void onCapture(i)} busy={working} />
      )}
      {working && (
        <p role="status" aria-live="polite" className="text-center text-body text-ink-2">
          {upload.isPending ? t.uploading : t.processing}
        </p>
      )}
      {(error || failed) && (
        <p role="alert" className="text-small text-danger">
          {failed ? (t.errors[failed as keyof typeof t.errors] ?? copy.common.genericError) : error}
        </p>
      )}
      {capture.data && status === "ready" && (
        <Results key={capture.data.id} capture={capture.data} onReset={() => setCaptureId(null)} />
      )}
      <p className="text-caption text-muted">{t.privacy}</p>
      <p className="text-caption text-muted">{t.tip}</p>
    </div>
  );
}
