"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useAuth } from "@/lib/auth/AuthProvider";
import { supabase } from "@/lib/auth/supabase";
import { copy } from "@/lib/copy/en";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function callbackUrl(): string {
  return `${window.location.origin}/auth/callback`;
}

export default function SignInPage() {
  const { session } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [sentTo, setSentTo] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const t = copy.auth;

  useEffect(() => {
    if (session) router.replace("/today");
  }, [session, router]);

  async function google() {
    setError(null);
    const { error: err } = await supabase().auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: callbackUrl() },
    });
    if (err) setError(copy.common.genericError);
  }

  async function sendCode(event: FormEvent) {
    event.preventDefault();
    const value = email.trim().toLowerCase();
    if (!EMAIL_RE.test(value)) {
      setError(t.invalidEmail);
      return;
    }
    setBusy(true);
    setError(null);
    const { error: err } = await supabase().auth.signInWithOtp({
      email: value,
      options: { emailRedirectTo: callbackUrl(), shouldCreateUser: true },
    });
    setBusy(false);
    if (err) setError(err.message || copy.common.genericError);
    else setSentTo(value);
  }

  async function verify(event: FormEvent) {
    event.preventDefault();
    if (!sentTo) return;
    setBusy(true);
    setError(null);
    const { error: err } = await supabase().auth.verifyOtp({
      email: sentTo,
      token: code.trim(),
      type: "email",
    });
    setBusy(false);
    if (err) setError(t.invalidCode);
  }

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col justify-center gap-6 px-screen-x py-8">
      <div className="flex flex-col gap-2">
        <span className="text-small font-semibold text-muted">{copy.appName}</span>
        <h1 className="m-0 font-display text-h1 font-bold tracking-[-0.01em]">{t.title}</h1>
        <p className="text-body text-ink-2">{t.subtitle}</p>
      </div>

      <Button variant="secondary" size="lg" fullWidth onClick={google}>
        {t.google}
      </Button>

      <div className="flex items-center gap-3 text-small text-muted" aria-hidden="true">
        <span className="h-px flex-1 bg-line" />
        {t.or}
        <span className="h-px flex-1 bg-line" />
      </div>

      {sentTo === null ? (
        <form onSubmit={sendCode} className="flex flex-col gap-3" noValidate>
          <Input
            label={t.emailLabel}
            type="email"
            autoComplete="email"
            inputMode="email"
            placeholder={t.emailPlaceholder}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <Button type="submit" size="lg" fullWidth loading={busy}>
            {t.sendCode}
          </Button>
        </form>
      ) : (
        <form onSubmit={verify} className="flex flex-col gap-3">
          <p className="text-small text-ink-2" aria-live="polite">
            {t.codeSentTo(sentTo)}
          </p>
          <Input
            label={t.codeLabel}
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={8}
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
          />
          <Button type="submit" size="lg" fullWidth loading={busy} disabled={code.length < 6}>
            {t.verify}
          </Button>
          <Button
            variant="ghost"
            onClick={() => {
              setSentTo(null);
              setCode("");
            }}
          >
            {t.useDifferentEmail}
          </Button>
        </form>
      )}

      {error && (
        <p role="alert" className="text-small text-danger">
          {error}
        </p>
      )}
      <p className="text-caption text-muted">{t.privacyLine}</p>
    </main>
  );
}
