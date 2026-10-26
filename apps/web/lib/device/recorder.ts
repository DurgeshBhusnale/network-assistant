/** MediaRecorder wrapper (FR-MEM-2): feature detection, best mime, level meter, 5-minute cap. */

export const MAX_RECORDING_MS = 5 * 60 * 1000;

const MIME_CANDIDATES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/mp4",
  "audio/ogg;codecs=opus",
];

export function recordingSupported(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.MediaRecorder !== "undefined" &&
    !!navigator.mediaDevices?.getUserMedia
  );
}

function pickMime(): string {
  return MIME_CANDIDATES.find((m) => MediaRecorder.isTypeSupported(m)) ?? "";
}

/** The mime our API accepts for upload (parameters stripped). */
export function baseMime(mime: string): string {
  return mime.split(";")[0]?.trim() || "audio/webm";
}

export type RecorderHandle = {
  stop: () => Promise<Blob>;
  cancel: () => void;
  level: () => number;
  mime: string;
};

export async function startRecording(onLimit: () => void): Promise<RecorderHandle> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const mime = pickMime();
  const recorder = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
  const chunks: Blob[] = [];
  recorder.ondataavailable = (e) => {
    if (e.data.size > 0) chunks.push(e.data);
  };

  const audioCtx = new AudioContext();
  const analyser = audioCtx.createAnalyser();
  analyser.fftSize = 256;
  audioCtx.createMediaStreamSource(stream).connect(analyser);
  const samples = new Uint8Array(analyser.frequencyBinCount);

  const release = () => {
    stream.getTracks().forEach((t) => t.stop());
    void audioCtx.close();
  };
  const limitTimer = window.setTimeout(onLimit, MAX_RECORDING_MS);
  recorder.start(1000);

  return {
    mime: recorder.mimeType || mime || "audio/webm",
    level: () => {
      analyser.getByteFrequencyData(samples);
      let sum = 0;
      for (const v of samples) sum += v;
      return samples.length ? sum / samples.length / 255 : 0;
    },
    stop: () =>
      new Promise<Blob>((resolve) => {
        window.clearTimeout(limitTimer);
        recorder.onstop = () => {
          release();
          resolve(new Blob(chunks, { type: recorder.mimeType || mime || "audio/webm" }));
        };
        recorder.stop();
      }),
    cancel: () => {
      window.clearTimeout(limitTimer);
      recorder.onstop = release;
      if (recorder.state !== "inactive") recorder.stop();
      else release();
    },
  };
}
