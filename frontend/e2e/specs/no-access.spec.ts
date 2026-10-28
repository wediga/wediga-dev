import { test, expect } from "@playwright/test";

// Where the backend sends a login through authentik whose account is in none
// of the known groups. authentik turns such accounts away first, so the test
// authentik never leads here and the page is checked on its own.
test("the no-access page explains the refusal", async ({ page }) => {
  await page.goto("/no-access");

  await expect(
    page.getByRole("heading", { name: "Kein Zugang" }),
  ).toBeVisible();
});
