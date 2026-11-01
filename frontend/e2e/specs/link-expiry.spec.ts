import { test, expect } from "@playwright/test";
import { login, openAdminPage } from "../helpers";

// A link created without a date gets the default lifetime from the backend, and
// the admin can move the expiry of an existing link or remove it. The exact
// default date is checked in the backend tests, so it is not repeated here.
test("a new link expires by default, and its expiry can be changed and removed", async ({
  page,
}) => {
  await login(page);

  await openAdminPage(page, "/admin/links");
  await page.getByPlaceholder("e.g. Acme Corp").fill("E2E Expiry");
  await page.getByRole("button", { name: "Create link" }).click();

  const item = page.locator("li", { hasText: "E2E Expiry" });
  const shown = item.getByText(/^Expires:/);
  await expect(shown).toHaveText(/^Expires: \d{4}-\d{2}-\d{2}$/);

  const field = item.getByLabel("Expires on");
  await field.fill("2030-01-31");
  await item.getByRole("button", { name: "Save expiry" }).click();
  await expect(shown).toHaveText("Expires: 2030-01-31");

  await field.fill("");
  await item.getByRole("button", { name: "Save expiry" }).click();
  await expect(shown).toHaveText("Expires: never");
  await expect(item.getByText("Active")).toBeVisible();
});
