import { defineConfig, devices } from "@playwright/test";

import { API_PORT, AUTH_FILE, BASE_URL, FRESH_AUTH_FILE, PORT } from "./e2e/env";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  // Two browsers at a time: the remote dev database pooler has few connections to share.
  workers: 2,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  // The dev database is in Seoul (~125 ms per round trip), so API-backed screens take 1-3 s.
  expect: { timeout: 15_000 },
  timeout: 90_000,
  globalSetup: "./e2e/global-setup.ts",
  globalTeardown: "./e2e/global-teardown.ts",
  use: {
    baseURL: BASE_URL,
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "signed-out",
      testMatch: /\.public\.spec\.ts$/,
      use: { ...devices["Pixel 7"] },
    },
    {
      name: "signed-in",
      testMatch: /\.app\.spec\.ts$/,
      use: { ...devices["Pixel 7"], storageState: AUTH_FILE },
    },
    {
      name: "onboarding",
      testMatch: /\.onboarding\.spec\.ts$/,
      use: { ...devices["Pixel 7"], storageState: FRESH_AUTH_FILE },
    },
  ],
  webServer: [
    {
      // API against the dev project, with fake AI so E2E never spends Groq credits.
      command: `uv run uvicorn --factory app.main:create_app --port ${API_PORT}`,
      cwd: "../api",
      // One shared test user makes many quick page loads; the product limit (60/min) would 429.
      env: { AI_MODE: "fake", RATE_LIMIT_GENERAL_PER_MINUTE: "1000" },
      url: `http://localhost:${API_PORT}/v1/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      // Production build: the service worker only registers in production.
      command: `pnpm exec next build && pnpm exec next start --port ${PORT}`,
      url: `${BASE_URL}/offline`,
      reuseExistingServer: !process.env.CI,
      timeout: 420_000,
    },
  ],
});
