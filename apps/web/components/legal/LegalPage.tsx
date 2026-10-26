import Link from "next/link";

import { copy } from "@/lib/copy/en";

type Section = { readonly heading: string; readonly body: string };

/** Public, static legal text (placeholder until legal review). */
export function LegalPage({ title, sections }: { title: string; sections: readonly Section[] }) {
  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col gap-5 px-screen-x py-8">
      <Link href="/sign-in" className="min-h-tap self-start py-3 text-small text-primary">
        {copy.legal.back}
      </Link>
      <h1 className="m-0 title">{title}</h1>
      <p className="text-caption text-muted">{copy.legal.reviewNote}</p>
      {sections.map((s) => (
        <section key={s.heading} className="flex flex-col gap-1">
          <h2 className="m-0 text-body font-semibold">{s.heading}</h2>
          <p className="text-small text-ink-2">{s.body}</p>
        </section>
      ))}
    </main>
  );
}
