import { expect, test } from "@playwright/test";

const TABS = [
  { name: "People", path: "/people", heading: "People" },
  { name: "Progress", path: "/progress", heading: "Progress" },
  { name: "Replies", path: "/replies", heading: "Did they reply?" },
  { name: "Today", path: "/today", heading: /^Good (morning|afternoon|evening), E2E$/ },
];

test.describe("app shell (signed in)", () => {
  test("root opens Today for an onboarded user", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/today$/);
    await expect(page.getByRole("heading", { level: 1, name: TABS[3]!.heading })).toBeVisible();
  });

  test("bottom nav has five items with the capture button raised", async ({ page }) => {
    await page.goto("/today");
    const nav = page.getByRole("navigation", { name: "Main" });

    await expect(nav.getByRole("link")).toHaveCount(5);
    await expect(nav.getByRole("link", { name: "Today" })).toHaveAttribute("aria-current", "page");

    const fab = await nav.getByRole("link", { name: "Capture by voice" }).boundingBox();
    const bar = await nav.boundingBox();
    expect(fab && bar).toBeTruthy();
    expect(fab!.y).toBeLessThan(bar!.y); // raised above the bar
    expect(fab!.width).toBeGreaterThanOrEqual(56);
  });

  test("tabs navigate and every tap target is at least 44 px", async ({ page }) => {
    await page.goto("/today");
    const nav = page.getByRole("navigation", { name: "Main" });

    for (const tab of TABS) {
      const link = nav.getByRole("link", { name: tab.name });
      const box = await link.boundingBox();
      expect(box!.height).toBeGreaterThanOrEqual(44);
      await link.click();
      await expect(page).toHaveURL(new RegExp(`${tab.path}$`));
      await expect(page.getByRole("heading", { level: 1, name: tab.heading })).toBeVisible();
    }

    await nav.getByRole("link", { name: "Capture by voice" }).click();
    await expect(page).toHaveURL(/\/capture$/);
  });

  test("no horizontal scroll at 390 px", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    const paths = [
      "/today",
      "/people",
      "/people/new",
      "/capture",
      "/progress",
      "/replies",
      "/settings",
      "/settings/goal",
      "/settings/privacy",
      "/settings/style",
      "/upgrade",
    ];
    for (const path of paths) {
      await page.goto(path);
      await expect(page.getByRole("heading", { level: 1 }).first(), path).toBeAttached();
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(overflow, path).toBeLessThanOrEqual(0);
    }
  });
});
