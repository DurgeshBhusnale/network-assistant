"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { FullScreenLoader } from "@/components/ui/FullScreenLoader";
import { useAuth } from "@/lib/auth/AuthProvider";
import { copy } from "@/lib/copy/en";

/** OAuth / magic-link landing. supabase-js exchanges the PKCE code on load (detectSessionInUrl). */
export default function AuthCallbackPage() {
  const { session, loading } = useAuth();
  const router = useRouter();
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (session) router.replace("/today");
  }, [session, router]);

  // Fail fast on an error in the URL; otherwise give the code exchange a few seconds.
  useEffect(() => {
    if (session) return;
    const params = new URLSearchParams(window.location.search);
    const hasError = params.has("error") || params.has("error_description");
    if (loading && !hasError) return;
    const timer = window.setTimeout(() => setFailed(true), hasError ? 0 : 8000);
    return () => window.clearTimeout(timer);
  }, [loading, session]);

  if (!failed) return <FullScreenLoader label={copy.auth.callbackTitle} />;
  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col justify-center gap-3 px-screen-x">
      <p role="alert" className="text-body text-ink-2">
        {copy.auth.callbackFailed}
      </p>
      <Link href="/sign-in" className="font-semibold">
        {copy.auth.backToSignIn}
      </Link>
    </main>
  );
}
