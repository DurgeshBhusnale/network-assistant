import { readFile, rm } from "node:fs/promises";

import { USER_FILE, env } from "./env";

export default async function globalTeardown() {
  const id = await readFile(USER_FILE, "utf8").catch(() => null);
  if (!id) return;
  const service = env("SUPABASE_SERVICE_ROLE_KEY");
  await fetch(`${env("NEXT_PUBLIC_SUPABASE_URL")}/auth/v1/admin/users/${id}`, {
    method: "DELETE",
    headers: { apikey: service, Authorization: `Bearer ${service}` },
  });
  await rm(USER_FILE, { force: true });
}
