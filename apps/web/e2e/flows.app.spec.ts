import { expect, test } from "@playwright/test";

// Runs against the dev project with AI_MODE=fake (see playwright.config.ts).
test.describe("core flows (signed in)", () => {
  test("add a person, add a note, and get a draft that nobody sends for you", async ({ page }) => {
    const name = `Priya E2E ${Date.now()}`;
    await page.goto("/people/new");
    await page.getByLabel("Name").fill(name);
    await page.getByLabel("Company").fill("Zoho");
    await page.getByRole("button", { name: "Add person" }).click();

    await expect(page).toHaveURL(/\/people\/[0-9a-f-]{36}$/);
    await expect(page.getByRole("heading", { level: 1, name })).toBeVisible();

    await page.getByRole("button", { name: "Add note" }).click();
    await page.getByRole("textbox", { name: "Note" }).fill("Met at eChai Pune");
    await page.getByRole("button", { name: "Save note" }).click();
    await expect(page.getByText("Met at eChai Pune")).toBeVisible();

    await page.getByRole("button", { name: "Draft message" }).click();
    await page.getByRole("dialog").getByRole("button").first().click();

    await expect(page).toHaveURL(/\/drafts\/[0-9a-f-]{36}$/);
    const message = page.getByLabel("Your message");
    await expect(message).not.toHaveValue("");
    await expect(page.getByText(/Nothing is sent until you tap send/)).toBeVisible();
    // No phone number: WhatsApp send is disabled; the user can only copy or mark as sent.
    await expect(page.getByRole("button", { name: "Send on WhatsApp" })).toBeDisabled();
  });

  test("tone change, edit, send on my own WhatsApp, then mark as sent", async ({
    page,
    context,
  }) => {
    // Regression R2. wa.me is stubbed: the test checks the link, not WhatsApp itself.
    await context.route("https://wa.me/**", (route) => route.fulfill({ body: "whatsapp" }));
    const name = `Arjun E2E ${Date.now()}`;
    await page.goto("/people/new");
    await page.getByLabel("Name").fill(name);
    await page.getByLabel("Phone").fill("+91 98765 43210");
    await page.getByLabel("Company").fill("Zoho");
    await page.getByRole("button", { name: "Add person" }).click();
    await expect(page.getByRole("heading", { level: 1, name })).toBeVisible();

    await page.getByRole("button", { name: "Draft message" }).click();
    await page.getByRole("dialog").getByRole("button").first().click();
    const message = page.getByLabel("Your message");
    await expect(message).not.toHaveValue("");

    await page.getByRole("button", { name: "Shorter" }).click();
    await expect(page.getByText(/free rewrites? left/)).toHaveText("2 free rewrites left");
    await message.fill("Hi Arjun, long time! How is Zoho treating you?");

    const popup = page.waitForEvent("popup");
    await page.getByRole("button", { name: "Send on WhatsApp" }).click();
    const wa = await popup;
    await expect(wa).toHaveURL(
      "https://wa.me/919876543210?text=Hi%20Arjun%2C%20long%20time%21%20How%20is%20Zoho%20treating%20you%3F",
    );
    await wa.close();
    // Coming back to the app asks whether it went out; nothing is recorded before that.
    await page.evaluate(() => document.dispatchEvent(new Event("visibilitychange")));
    await page.getByRole("button", { name: "Yes, sent" }).click();
    await expect(page.getByText(/Marked as sent/)).toBeVisible();
  });

  test("goal settings show the current goal", async ({ page }) => {
    await page.goto("/settings/goal");
    await expect(page.getByLabel("Role you want")).toHaveValue("Backend Engineer");
    await expect(page.getByText("Zoho")).toBeVisible();
    await expect(page.getByRole("button", { name: "Pause" })).toBeVisible();
  });

  test("privacy settings show saved choices and guard account deletion", async ({ page }) => {
    await page.goto("/settings/privacy");
    await expect(page.getByRole("checkbox", { name: /Import my contacts/ })).toBeChecked();
    await expect(page.getByRole("checkbox", { name: /Message me on WhatsApp/ })).not.toBeChecked();
    const del = page.getByRole("button", { name: "Delete my account" });
    await expect(del).toBeDisabled();
    await page.getByLabel("Type DELETE to confirm").fill("DELETE");
    await expect(del).toBeEnabled();
  });

  test("admin metrics are refused for a normal user", async ({ page }) => {
    await page.goto("/admin");
    await expect(page.getByText("Admins only.")).toBeVisible();
  });
});
