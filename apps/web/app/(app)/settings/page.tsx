"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useId, useMemo, useState, type ReactNode } from "react";

import { NotificationsCard } from "@/components/settings/NotificationsCard";
import { PlanCard } from "@/components/settings/PlanCard";
import { WhatsAppCard } from "@/components/settings/WhatsAppCard";
import { PageHeader } from "@/components/shell/PageHeader";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { ApiError } from "@/lib/api/client";
import { useMe, useUpdateMe, type Profile } from "@/lib/api/hooks/account";
import { signOut } from "@/lib/auth/AuthProvider";
import { copy } from "@/lib/copy/en";

type Language = Profile["language"];
const LANGUAGES = Object.keys(copy.settings.languages) as Language[];

function timezones(current: string): string[] {
  const all =
    typeof Intl.supportedValuesOf === "function"
      ? Intl.supportedValuesOf("timeZone")
      : ["Asia/Kolkata", "Asia/Dubai", "Asia/Singapore", "Europe/London", "America/New_York"];
  return all.includes(current) ? all : [current, ...all];
}

function Select({
  label,
  value,
  onChange,
  children,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  children: ReactNode;
}) {
  const id = useId();
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-small font-semibold">
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-[46px] rounded-button border border-line-strong bg-surface px-3 text-body text-ink"
      >
        {children}
      </select>
    </div>
  );
}

export default function SettingsPage() {
  const me = useMe();
  return (
    <>
      <PageHeader title={copy.settings.title} />
      {me.data && <SettingsForm profile={me.data} />}
    </>
  );
}

function SettingsForm({ profile }: { profile: Profile }) {
  const update = useUpdateMe();
  const router = useRouter();
  const t = copy.settings;

  const [name, setName] = useState(profile.display_name ?? "");
  const [language, setLanguage] = useState<Language>(profile.language);
  const [timezone, setTimezone] = useState(profile.timezone);
  const [nudge, setNudge] = useState(profile.nudge_time);
  const [message, setMessage] = useState<string | null>(null);

  const zones = useMemo(() => timezones(timezone), [timezone]);

  async function save() {
    setMessage(null);
    try {
      await update.mutateAsync({
        display_name: name.trim() || null,
        language,
        timezone,
        nudge_time: nudge,
      });
      setMessage(t.saved);
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : copy.common.genericError);
    }
  }

  async function logout() {
    await signOut();
    router.replace("/sign-in");
  }

  return (
    <div className="flex flex-col gap-gap-cards px-screen-x pt-2">
      <Card>
        <h2 className="m-0 font-display text-h2 font-semibold">{t.profile}</h2>
        <Input
          label={t.nameLabel}
          autoComplete="name"
          value={name}
          maxLength={80}
          onChange={(e) => setName(e.target.value)}
        />
        <Select
          label={t.languageLabel}
          value={language}
          onChange={(v) => setLanguage(v as Language)}
        >
          {LANGUAGES.map((l) => (
            <option key={l} value={l}>
              {t.languages[l]}
            </option>
          ))}
        </Select>
        <Select label={t.timezoneLabel} value={timezone} onChange={setTimezone}>
          {zones.map((z) => (
            <option key={z} value={z}>
              {z}
            </option>
          ))}
        </Select>
        <Input
          label={t.nudgeLabel}
          type="time"
          value={nudge}
          onChange={(e) => setNudge(e.target.value)}
        />
        <Button loading={update.isPending} onClick={save}>
          {t.save}
        </Button>
        {message && (
          <p role="status" className="text-small text-muted">
            {message}
          </p>
        )}
      </Card>

      <PlanCard />

      <NotificationsCard profile={profile} />

      <WhatsAppCard />

      <Link
        href="/settings/style"
        className="flex min-h-tap flex-col gap-0.5 rounded-card border border-line bg-surface p-card text-ink no-underline"
      >
        <span className="text-body font-semibold">{t.writingStyle}</span>
        <span className="text-small text-muted">{t.writingStyleBody}</span>
      </Link>

      <Card>
        <h2 className="m-0 font-display text-h2 font-semibold">{t.account}</h2>
        {profile.email && <p className="text-small text-ink-2">{t.signedInAs(profile.email)}</p>}
        <Button variant="secondary" onClick={logout}>
          {t.signOut}
        </Button>
      </Card>
    </div>
  );
}
