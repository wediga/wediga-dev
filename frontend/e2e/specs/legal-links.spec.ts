import { test, expect } from "@playwright/test";

// The privacy policy has to be one click away from every public page. The
// landing and the quiet pages are checked here, the recruiter views in the
// recruiter link test, because only that test has a recruiter session.
test.use({ reducedMotion: "reduce" });

test("the landing footer leads to the privacy policy", async ({ page }) => {
  await page.goto("/");
  // The quiet landing keeps its footer inside main, where a footer has no
  // contentinfo role, so the one link on the page is found directly.
  await page.getByRole("link", { name: "Datenschutz" }).click();

  await expect(page).toHaveURL(/\/datenschutz$/);
  await expect(
    page.getByRole("heading", { name: "Datenschutzerklärung" }),
  ).toBeVisible();
  // The person responsible comes from the impressum, as the address to write to.
  await expect(
    page.locator("main").getByRole("link", { name: /@/ }),
  ).toBeVisible();
});

test("the quiet pages link to impressum and privacy policy", async ({
  page,
}) => {
  await page.goto("/datenschutz");
  const footer = page.getByRole("contentinfo");

  await expect(footer.getByRole("link", { name: "Impressum" })).toBeVisible();
  await expect(
    footer.getByRole("link", { name: "Datenschutz" }),
  ).toBeVisible();
});
