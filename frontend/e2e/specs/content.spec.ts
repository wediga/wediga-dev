import { test, expect } from "@playwright/test";
import { login, openAdminPage } from "../helpers";

// An admin edit must reach the public view. About is read without a session, so
// the landing page is the cleanest place to prove the edit went through the
// full BFF-to-backend write path and back out through a public read.
test("an about edit in the admin appears on the public landing page", async ({
  page,
}) => {
  await login(page);

  await openAdminPage(page, "/admin/about");
  await expect(page.getByRole("heading", { name: "About" })).toBeVisible();

  const marker = `E2E about marker ${Date.now()}`;
  await page.locator("textarea").fill(`# About\n\n${marker}`);
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page.getByText("Saved")).toBeVisible();

  // The public landing page reads about without a session and must show it.
  await page.goto("/");
  await expect(page.getByText(marker)).toBeVisible();
});
