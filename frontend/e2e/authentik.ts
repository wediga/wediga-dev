import { Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { totpCode } from "./totp";

// The test accounts that deploy/authentik-test/setup.py creates, and the way
// through authentik's own login forms with password and TOTP.

type Account = { password: string; totp_secret: string };

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

// Fill in authentik's login forms on the current page. authentik accepts each
// TOTP code only once, so an account logs in at most once per 30 seconds.
export async function logInAtAuthentik(
  page: Page,
  username: string,
): Promise<void> {
  const { password, totp_secret } = account(username);

  await page.getByRole("textbox", { name: /username/i }).fill(username);
  await page.getByRole("button", { name: "Log in" }).click();
  await page.getByRole("textbox", { name: "Password" }).fill(password);
  await page.getByRole("button", { name: "Continue" }).click();
  await page
    .getByRole("textbox", { name: /code/i })
    .fill(totpCode(totp_secret));
  await page.getByRole("button", { name: "Continue" }).click();
}
