import { expect, test } from "@playwright/test";

import { env } from "./env";

test.describe("signed out", () => {
  test("app routes send you to sign in", async ({ page }) => {
    await page.goto("/today");
    await expect(page).toHaveURL(/\/sign-in$/);
    await expect(
      page.getByRole("heading", { level: 1, name: "Get referred by people you already know" }),
    ).toBeVisible();
  });

  test("privacy policy and terms are public and marked for legal review", async ({ page }) => {
    await page.goto("/sign-in");
    await page.getByRole("link", { name: "Privacy policy" }).click();
    await expect(page.getByRole("heading", { level: 1, name: "Privacy policy" })).toBeVisible();
    await expect(page.getByText(/to be reviewed by a lawyer/)).toBeVisible();

    await page.goto("/terms");
    await expect(page.getByRole("heading", { level: 1, name: "Terms of use" })).toBeVisible();
  });

  test("security headers are set", async ({ request }) => {
    const res = await request.get("/sign-in");
    const h = res.headers();
    expect(h["content-security-policy"]).toContain("frame-ancestors 'none'");
    // Whichever Supabase the build points at: the cloud project locally, the CLI stack in CI.
    expect(h["content-security-policy"]).toContain(
      `connect-src 'self' ${env("NEXT_PUBLIC_SUPABASE_URL")}`,
    );
    expect(h["strict-transport-security"]).toContain("max-age=");
    expect(h["x-frame-options"]).toBe("DENY");
  });
});
