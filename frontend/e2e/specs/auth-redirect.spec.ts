import { test, expect } from "@playwright/test";
import { login } from "../helpers";

// Regression for the known integration bug: after login the session cookie is
// set and the BFF accepts it, but the server-component gate forwarded the same
// cookie differently and rejected it, bouncing the admin back to /login. This
// test fails before the gate fix and passes after it.
test("admin lands in the admin area after login and is not bounced to /login", async ({
  page,
}) => {
  await login(page);

  // The gate accepted the session, so the admin overview renders instead of a
  // redirect to /login.
  await expect(page).toHaveURL(/\/admin$/);

  // A second protected admin page must also render, not redirect.
  await page.goto("/admin/about");
  await expect(page).toHaveURL(/\/admin\/about$/);
  await expect(page.getByRole("heading", { name: "About" })).toBeVisible();
});
