import { expect, test } from "@playwright/test";

// ADR-0011: at 1440 × 900 the app uses the web layout (sidebar instead of the bottom nav).
test.describe("desktop web layout", () => {
  test("sidebar navigates; no bottom nav, no horizontal scroll", async ({ page }) => {
    await page.goto("/today");
    const nav = page.getByRole("navigation", { name: "Main" });
    await expect(nav).toHaveCount(1); // the bottom nav is hidden at this width
    await expect(nav.getByRole("link", { name: "Today" })).toHaveAttribute("aria-current", "page");
    await expect(page.getByTestId("capture-fab")).toBeHidden();

    for (const [name, path, heading] of [
      ["People", "/people", "People"],
      ["Progress", "/progress", "Progress"],
      ["Replies", "/replies", "Did they reply?"],
    ] as const) {
      await nav.getByRole("link", { name }).click();
      await expect(page).toHaveURL(new RegExp(`${path}$`));
      await expect(page.getByRole("heading", { level: 1, name: heading })).toBeAttached();
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(overflow, path).toBeLessThanOrEqual(0);
    }

    await page.getByRole("link", { name: "Voice capture" }).click();
    await expect(page).toHaveURL(/\/capture$/);
    // Voice capture is full-bleed: no sidebar.
    await expect(page.getByRole("navigation", { name: "Main" })).toHaveCount(0);
  });

  test("detail and settings pages keep the sidebar and fit the width", async ({ page }) => {
    for (const path of ["/people/new", "/settings", "/settings/goal", "/settings/privacy"]) {
      await page.goto(path);
      await expect(page.getByRole("heading", { level: 1 }).first(), path).toBeAttached();
      await expect(page.getByRole("navigation", { name: "Main" }), path).toBeVisible();
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(overflow, path).toBeLessThanOrEqual(0);
    }
  });
});
