/** Web push subscription (installed PWA). Feature-detected; the API stores the subscription. */

export function pushSupported(): boolean {
  return (
    typeof window !== "undefined" &&
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window
  );
}

function keyBytes(base64: string): Uint8Array<ArrayBuffer> {
  const padding = "=".repeat((4 - (base64.length % 4)) % 4);
  const raw = window.atob((base64 + padding).replace(/-/g, "+").replace(/_/g, "/"));
  const bytes = new Uint8Array(new ArrayBuffer(raw.length));
  for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
  return bytes;
}

export type BrowserSubscription = { endpoint: string; keys: Record<string, string> };

/** Asks permission (must follow a tap) and subscribes. Null if denied or unsupported. */
export async function subscribePush(publicKey: string): Promise<BrowserSubscription | null> {
  if (!pushSupported()) return null;
  if ((await Notification.requestPermission()) !== "granted") return null;
  const registration = await navigator.serviceWorker.ready;
  const sub =
    (await registration.pushManager.getSubscription()) ??
    (await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: keyBytes(publicKey),
    }));
  const json = sub.toJSON();
  return {
    endpoint: json.endpoint ?? sub.endpoint,
    keys: (json.keys ?? {}) as Record<string, string>,
  };
}

export async function currentPushSubscription(): Promise<BrowserSubscription | null> {
  if (!pushSupported()) return null;
  const registration = await navigator.serviceWorker.getRegistration();
  const sub = await registration?.pushManager.getSubscription();
  if (!sub) return null;
  const json = sub.toJSON();
  return {
    endpoint: json.endpoint ?? sub.endpoint,
    keys: (json.keys ?? {}) as Record<string, string>,
  };
}

export async function unsubscribePush(): Promise<BrowserSubscription | null> {
  const current = await currentPushSubscription();
  const registration = await navigator.serviceWorker.getRegistration();
  await (await registration?.pushManager.getSubscription())?.unsubscribe();
  return current;
}
