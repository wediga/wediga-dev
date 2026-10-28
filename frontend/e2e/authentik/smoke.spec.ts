import { test, expect } from "@playwright/test";
import { logInAtAuthentik } from "../authentik";

// The test authentik from deploy/authentik-test is up and set up: the admin
// test account gets through authentik's own login with password and TOTP. This
// only checks the test environment, wediga.dev is not involved yet.

const ADMIN_ACCOUNT = "test-admin";

test("the admin test account logs in with password and TOTP", async ({
  page,
}) => {
  await page.goto("/");
  await logInAtAuthentik(page, ADMIN_ACCOUNT);

  // A finished login lands on authentik's user interface.
  await expect(page).toHaveURL(/\/if\/user\//);
});
