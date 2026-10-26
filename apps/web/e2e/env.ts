import { loadEnvConfig } from "@next/env";
import path from "node:path";

// Same root .env as the app (next.config.ts).
loadEnvConfig(path.resolve(__dirname, "../../.."), false, undefined, true);

export const PORT = 3100;
// Its own API (fake AI), never the developer's `pnpm dev` server on :8000 (which may run live AI).
export const API_PORT = Number(process.env.E2E_API_PORT ?? 8100);
export const BASE_URL = `http://localhost:${PORT}`;
export const AUTH_FILE = path.join(__dirname, ".auth", "user.json");
export const FRESH_AUTH_FILE = path.join(__dirname, ".auth", "fresh-user.json");
export const USER_FILE = path.join(__dirname, ".auth", "user-ids.txt");

export function env(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is not set (root .env)`);
  return value;
}
