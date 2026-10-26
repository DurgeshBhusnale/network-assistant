import type { Metadata } from "next";

import { LegalPage } from "@/components/legal/LegalPage";
import { copy } from "@/lib/copy/en";

export const metadata: Metadata = { title: copy.legal.privacyTitle };

export default function PrivacyPolicyPage() {
  return (
    <LegalPage
      title={copy.legal.privacyTitle}
      sections={[...copy.consents.noticeSections, ...copy.legal.privacyExtra]}
    />
  );
}
