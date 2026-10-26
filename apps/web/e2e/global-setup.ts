import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

import { AUTH_FILE, BASE_URL, FRESH_AUTH_FILE, USER_FILE, env } from "./env";

type Session = { access_token: string };

/** A throwaway confirmed user in the dev project, signed in with a password grant. */
async function createUser(): Promise<{ id: string; session: Session }> {
  const url = env("NEXT_PUBLIC_SUPABASE_URL");
  const anon = env("NEXT_PUBLIC_SUPABASE_ANON_KEY");
  const service = env("SUPABASE_SERVICE_ROLE_KEY");
  const email = `e2e-${crypto.randomUUID().slice(0, 8)}@example.com`;
  const password = crypto.randomUUID();

  const created = await fetch(`${url}/auth/v1/admin/users`, {
    method: "POST",
    headers: {
      apikey: service,
      Authorization: `Bearer ${service}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password, email_confirm: true }),
  });
  if (!created.ok) throw new Error(`create user failed: ${created.status}`);
  const { id } = (await created.json()) as { id: string };

  const tokenRes = await fetch(`${url}/auth/v1/token?grant_type=password`, {
    method: "POST",
    headers: { apikey: anon, "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!tokenRes.ok) throw new Error(`sign in failed: ${tokenRes.status}`);
  return { id, session: (await tokenRes.json()) as Session };
}

/** supabase-js keeps the session in localStorage under sb-<project ref>-auth-token. */
async function saveStorageState(file: string, session: Session) {
  const ref = new URL(env("NEXT_PUBLIC_SUPABASE_URL")).hostname.split(".")[0];
  await writeFile(
    file,
    JSON.stringify({
      cookies: [],
      origins: [
        {
          origin: BASE_URL,
          localStorage: [{ name: `sb-${ref}-auth-token`, value: JSON.stringify(session) }],
        },
      ],
    }),
  );
}

/**
 * Two throwaway users: one fully onboarded through the real API (most specs), one fresh from
 * sign-in (the onboarding spec). global-teardown deletes both; cascade removes every row.
 */
export default async function globalSetup() {
  await mkdir(path.dirname(USER_FILE), { recursive: true });
  const ready = await createUser();
  const fresh = await createUser();
  await writeFile(USER_FILE, [ready.id, fresh.id].join("\n"));

  const api = async (method: string, route: string, body: unknown) => {
    const res = await fetch(`${BASE_URL}/api${route}`, {
      method,
      headers: {
        Authorization: `Bearer ${ready.session.access_token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`${method} ${route} failed: ${res.status}`);
  };
  await api("PUT", "/v1/privacy/consents", {
    accept_notice: true,
    consents: { contacts: true, voice: true, whatsapp: false, analytics: false },
  });
  await api("PATCH", "/v1/me", { display_name: "E2E Tester", timezone: "Asia/Kolkata" });
  await api("POST", "/v1/goals", {
    pack_id: "career_sprint",
    params: { role: "Backend Engineer", companies: ["Zoho"] },
  });
  await api("PATCH", "/v1/me", { onboarding_step: "done" });

  await saveStorageState(AUTH_FILE, ready.session);
  await saveStorageState(FRESH_AUTH_FILE, fresh.session);
}
