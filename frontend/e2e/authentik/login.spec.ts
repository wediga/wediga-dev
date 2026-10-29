import { test, expect, Page } from "@playwright/test";
import { logInAtAuthentik } from "../authentik";

// The login of wediga.dev through the test authentik, with the accounts from
// setup.py. Each account logs in once per run, because authentik accepts each
// TOTP code only once.

// authentik's logout flow for wediga.dev ends on the live site. The tests
// answer that address themselves, so they never reach it.
const LIVE_SITE = "https://www.wediga.dev/";

async function logInThroughAuthentik(page: Page, username: string) {
  await page.goto("/auth/login");
  await logInAtAuthentik(page, username);
}

async function expectNoAdminAccess(page: Page) {
  await page.goto("/admin");
  await expect(page).toHaveURL(/\/login$/);
}

test("the admin gets into /admin through the link on /login, and logging out ends the authentik session as well", async ({
  page,
}) => {
  await page.route(`${LIVE_SITE}**`, (route) =>
    route.fulfill({ contentType: "text/html", body: "live site" }),
  );

  await page.goto("/login");
  await page
    .getByRole("link", { name: "Mit wediga.dev-Konto anmelden" })
    .click();
  await logInAtAuthentik(page, "test-admin");
  await expect(page).toHaveURL(/\/admin$/);
  await expect(page.getByRole("link", { name: "Overview" })).toBeVisible();

  await page.getByRole("button", { name: "Logout" }).click();
  await expect(page).toHaveURL(LIVE_SITE);
  await expectNoAdminAccess(page);

  // A new login asks for the account again instead of returning at once.
  await page.goto("/auth/login");
  await expect(page.getByRole("textbox", { name: /username/i })).toBeVisible();
});

test("a friend logs in but gets no admin access", async ({ page }) => {
  await logInThroughAuthentik(page, "test-friend");
  await expect(page).toHaveURL(/\/hub$/);

  await expectNoAdminAccess(page);
});

test("an account without a group is turned away by authentik", async ({
  page,
}) => {
  await logInThroughAuthentik(page, "test-nogroup");
  await expect(page.getByText("Permission denied")).toBeVisible();

  await expectNoAdminAccess(page);
});
