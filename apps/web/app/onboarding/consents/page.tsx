"use client";

import { useRouter } from "next/navigation";

import { ConsentsForm } from "@/components/privacy/ConsentsForm";
import { FullScreenLoader } from "@/components/ui/FullScreenLoader";
import { useConsents } from "@/lib/api/hooks/account";

export default function ConsentsPage() {
  const consents = useConsents();
  const router = useRouter();
  if (consents.isPending) return <FullScreenLoader />;
  // The app gate sends the user on to the next onboarding step, or home.
  return <ConsentsForm initial={consents.data} onSaved={() => router.replace("/today")} />;
}
