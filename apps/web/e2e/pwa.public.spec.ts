import { expect, test } from "@playwright/test";

type ManifestIcon = { src: string; sizes: string; type: string; purpose?: string };

test.describe("PWA installability", () => {
  test("manifest has the fields Chrome needs to install", async ({ request }) => {
    const response = await request.get("/manifest.webmanifest");
    expect(response.ok()).toBe(true);
    const manifest = await response.json();

    expect(manifest.name).toBeTruthy();
    expect(manifest.short_name).toBeTruthy();
    expect(manifest.start_url).toBe("/today");
    expect(manifest.display).toBe("standalone");

    const icons: ManifestIcon[] = manifest.icons;
    expect(icons.some((i) => i.sizes === "192x192")).toBe(true);
    expect(icons.some((i) => i.sizes === "512x512" && i.purpose !== "maskable")).toBe(true);
    expect(icons.some((i) => i.purpose === "maskable")).toBe(true);
    for (const icon of icons) {
      const res = await request.get(icon.src);
      expect(res.ok(), icon.src).toBe(true);
      expect(res.headers()["content-type"]).toContain("image/png");
    }
  });

  test("service worker controls the page and serves the offline shell", async ({
    page,
    context,
  }) => {
    await page.goto("/today");
    await page.evaluate(async () => {
      await navigator.serviceWorker.ready;
    });
    await page.reload();
    expect(await page.evaluate(() => navigator.serviceWorker.controller !== null)).toBe(true);

    await context.setOffline(true);
    await page.goto("/people");
    await expect(page.getByRole("heading", { level: 1, name: "You're offline" })).toBeVisible();
    await context.setOffline(false);
  });

  test("service worker is served uncached", async ({ request }) => {
    const res = await request.get("/sw.js");
    expect(res.ok()).toBe(true);
    expect(res.headers()["cache-control"]).toContain("no-store");
  });
});
