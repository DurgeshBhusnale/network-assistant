export type ServiceWorkerStatus = "registered" | "unsupported" | "failed";

/** Registers the offline-shell service worker (public/sw.js) where supported. */
export async function registerServiceWorker(): Promise<ServiceWorkerStatus> {
  if (typeof navigator === "undefined" || !("serviceWorker" in navigator)) return "unsupported";
  try {
    await navigator.serviceWorker.register("/sw.js", { scope: "/", updateViaCache: "none" });
    return "registered";
  } catch {
    return "failed";
  }
}
