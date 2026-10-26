import { copy } from "@/lib/copy/en";

/** Served by the service worker when a navigation fails offline. Static: no data, no API. */
export default function OfflinePage() {
  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col justify-center gap-3 px-screen-x">
      <h1 className="m-0 title">{copy.offline.title}</h1>
      <p className="text-body text-ink-2">{copy.offline.body}</p>
      <a
        href="/today"
        className="inline-flex min-h-cta items-center justify-center rounded-button-lg bg-grad px-7 text-[16px] font-semibold text-on-primary no-underline shadow-cta hover:text-on-primary"
      >
        {copy.offline.retry}
      </a>
    </main>
  );
}
