import { expect, test } from "@playwright/test";

// Regression R1: consents → goal → import LinkedIn CSV → Today has suggestions.
// The user starts signed in but with nothing else (sign-in itself needs email or Google).
const CSV = [
  "Notes:",
  '"When exporting your connection data, you may notice that some of the email addresses are missing."',
  "",
  "First Name,Last Name,URL,Email Address,Company,Position,Connected On",
  "Kavya,Rao,https://www.linkedin.com/in/kavya-rao-e2e,,Zoho,SDE 2,01 Jan 2024",
  "Imran,Shaikh,https://www.linkedin.com/in/imran-e2e,,Zoho Corp,PM,02 Feb 2024",
  "Ravi,Kumar,https://www.linkedin.com/in/ravi-e2e,,Infosys,Lead,03 Mar 2024",
].join("\n");

test("a new user gets from consents to a daily list", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/onboarding\/consents$/);
  const boxes = page.getByRole("checkbox");
  for (const box of await boxes.all()) await expect(box).not.toBeChecked();
  await page.getByRole("checkbox", { name: /read the privacy notice/ }).check();
  await page.getByRole("checkbox", { name: /Import my contacts/ }).check();
  await page.getByRole("button", { name: "Continue" }).click();

  await expect(page).toHaveURL(/\/onboarding\/goal$/);
  await page.getByLabel("Role you want").fill("Backend Engineer");
  await page.getByRole("button", { name: "+ Add" }).click();
  await page.getByLabel("Company name").fill("Zoho");
  await page.getByLabel("Company name").press("Enter");
  await page.getByRole("button", { name: "Continue" }).click();

  await expect(page).toHaveURL(/\/onboarding\/import$/);
  const chooser = page.waitForEvent("filechooser");
  await page.getByRole("button", { name: "Upload CSV" }).click();
  await (
    await chooser
  ).setFiles({
    name: "Connections.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(CSV),
  });
  await expect(page.getByText("3 new · 0 merged with people you have · 0 skipped")).toBeVisible();
  await page.getByRole("button", { name: "Add these people" }).click();
  await page.getByRole("button", { name: "Continue with 3 people" }).click();

  await expect(page).toHaveURL(/\/onboarding\/style$/);
  await page.getByRole("button", { name: "Skip for now" }).click();

  await expect(page).toHaveURL(/\/today$/);
  // Both Zoho people rank above the Infosys contact for a Zoho goal.
  await expect(page.getByText("Kavya Rao").first()).toBeVisible();
  await expect(page.getByText("Imran Shaikh").first()).toBeVisible();
});
