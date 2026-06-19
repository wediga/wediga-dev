import { Page, expect } from "@playwright/test";

// The admin password matches the one the Playwright config passes to the
// backend; both read the same environment variable with the same local default.
export const ADMIN_PASSWORD =
  process.env.E2E_ADMIN_PASSWORD ?? "e2e-admin-password";

// Log in through the real login form, which posts to the BFF and lands the
// browser on /admin once the session cookie is set.
export async function login(page: Page): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Passwort").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Anmelden" }).click();
  // The admin nav only renders once the layout gate accepts the session.
  await expect(page.getByRole("link", { name: "Overview" })).toBeVisible();
}

// Open an admin form page and wait for its CSRF token to load. The admin forms
// fetch the token after mount and send it on every write, so a write fired
// before the token arrived would be rejected. The listener is armed before the
// navigation, so the response is never missed.
export async function openAdminPage(page: Page, path: string): Promise<void> {
  const csrf = page.waitForResponse(
    (response) => response.url().includes("/api/csrf") && response.ok(),
  );
  await page.goto(path);
  await csrf;
}
