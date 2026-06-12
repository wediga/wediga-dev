import { test, expect } from "@playwright/test";
import { login } from "../helpers";

// Logout must lock the protected pages again: once the session is cleared, the
// admin gate sends the visitor back to the login page.
test("logout locks the protected pages again", async ({ page }) => {
  await login(page);

  await page.getByRole("button", { name: "Logout" }).click();
  // The logout handler clears the session and pushes to /login.
  await expect(page).toHaveURL(/\/login$/);

  // A direct visit to the admin area is now bounced back to login.
  await page.goto("/admin");
  await expect(page).toHaveURL(/\/login$/);
});
