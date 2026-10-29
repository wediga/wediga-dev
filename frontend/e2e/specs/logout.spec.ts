import { test, expect } from "@playwright/test";
import { login } from "../helpers";

// Logout must lock the protected pages again: once the session is cleared, the
// admin gate sends the visitor away from the admin area.
test("logout locks the protected pages again", async ({ page }) => {
  await login(page);

  await page.getByRole("button", { name: "Logout" }).click();
  // The logout handler clears the session and pushes to /login.
  await expect(page).toHaveURL(/\/login$/);

  // A direct visit to the admin area is now sent to authentik, or to /login
  // while the login through authentik is switched off.
  await page.goto("/admin");
  expect(new URL(page.url()).pathname).not.toMatch(/^\/admin/);
});
