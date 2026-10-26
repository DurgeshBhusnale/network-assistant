import type { Metadata } from "next";

import { LegalPage } from "@/components/legal/LegalPage";
import { copy } from "@/lib/copy/en";

export const metadata: Metadata = { title: copy.legal.termsTitle };

export default function TermsPage() {
  return <LegalPage title={copy.legal.termsTitle} sections={copy.legal.termsSections} />;
}
