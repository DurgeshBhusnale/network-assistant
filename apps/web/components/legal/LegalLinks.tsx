import Link from "next/link";

import { copy } from "@/lib/copy/en";

export function LegalLinks() {
  return (
    <p className="flex gap-4 text-caption">
      <Link href="/privacy" className="inline-flex min-h-tap items-center text-primary">
        {copy.legal.privacyTitle}
      </Link>
      <Link href="/terms" className="inline-flex min-h-tap items-center text-primary">
        {copy.legal.termsTitle}
      </Link>
    </p>
  );
}
