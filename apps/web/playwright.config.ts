import { defineConfig, devices } from "@playwright/test";

const PORT = 3100;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: "retain-on-failure",
  },
  projects: [{ name: "pixel-7", use: { ...devices["Pixel 7"] } }],
  // Production build: the service worker only registers in production.
  webServer: {
    command: `pnpm exec next build && pnpm exec next start --port ${PORT}`,
    url: `http://localhost:${PORT}/offline`,
    reuseExistingServer: !process.env.CI,
    timeout: 240_000,
  },
});
