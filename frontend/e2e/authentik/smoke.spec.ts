import { test, expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import { totpCode } from "../totp";

// The test authentik from deploy/authentik-test is up and set up: the admin
// test account gets through authentik's own login with password and TOTP. This
// only checks the test environment, wediga.dev is not involved yet.

type Account = { password: string; totp_secret: string };

const ADMIN_ACCOUNT = "test-admin";

function account(username: string): Account {
  const file = process.env.AUTHENTIK_ACCOUNTS;

  if (!file) {
    throw new Error("AUTHENTIK_ACCOUNTS must point at the file setup.py wrote");
  }

  // The account names are set in setup.py, so a missing one means the two
  // files disagree.
  const found = JSON.parse(readFileSync(file, "utf-8"))[username];

  if (!found) {
    throw new Error(`setup.py created no account "${username}"`);
  }

  return found;
}

test("the admin test account logs in with password and TOTP", async ({
  page,
}) => {
  const admin = account(ADMIN_ACCOUNT);

  await page.goto("/");
  await page.getByRole("textbox", { name: /username/i }).fill(ADMIN_ACCOUNT);
  await page.getByRole("button", { name: "Log in" }).click();
  await page.getByRole("textbox", { name: "Password" }).fill(admin.password);
  await page.getByRole("button", { name: "Continue" }).click();
  await page
    .getByRole("textbox", { name: /code/i })
    .fill(totpCode(admin.totp_secret));
  await page.getByRole("button", { name: "Continue" }).click();

  // A finished login lands on authentik's user interface.
  await expect(page).toHaveURL(/\/if\/user\//);
});
