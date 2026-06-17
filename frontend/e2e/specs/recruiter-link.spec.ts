import { test, expect } from "@playwright/test";
import { login, openAdminPage } from "../helpers";

// A recruiter link must unlock the recruiter view through /r/{token}, and
// revoking it must lock the view again on the very next read. Since Phase H2 the
// magic link lands on the landing page, not straight in the portfolio: the
// landing sees the fresh recruiter session and offers the door onward. The
// visitor runs in a separate browser context, so it carries only the recruiter
// session and never the admin one.
test("a recruiter link lands on the landing, opens the portfolio through the access door, and revocation locks it again", async ({
  page,
  browser,
}) => {
  await login(page);

  await openAdminPage(page, "/admin/links");
  await page.getByPlaceholder("e.g. Acme Corp").fill("E2E Recruiter");
  await page.getByRole("button", { name: "Create link" }).click();

  // The plaintext magic-link URL is shown exactly once, in a code block.
  const code = page.locator("code");
  await expect(code).toBeVisible();
  const url = (await code.textContent())?.trim() ?? "";
  expect(url).toContain("/r/");

  // The visitor uses reduced motion, so the landing renders its flat, interactive
  // column with the access door rather than the WebGL ride.
  const visitor = await browser.newContext({ reducedMotion: "reduce" });
  const visitorPage = await visitor.newPage();
  await visitorPage.goto(url);

  // Redeeming the token starts the recruiter session and now lands on the
  // landing page (origin root), not directly in the portfolio.
  await expect(visitorPage).toHaveURL(/^http:\/\/localhost:\d+\/$/);

  // With a valid recruiter session the access door leads onward to the portfolio.
  await visitorPage.getByRole("link", { name: "Weiter ins Portfolio" }).click();
  await expect(visitorPage).toHaveURL(/\/portfolio$/);
  await expect(
    visitorPage.getByRole("heading", { name: "Portfolio" }),
  ).toBeVisible();
  // The seeded project shows in the gated recruiter view, proving the gated
  // read carried the recruiter session through to the backend.
  await expect(visitorPage.getByText("Example Project")).toBeVisible();

  // The admin revokes the link.
  await page.getByRole("button", { name: "Revoke" }).first().click();
  await expect(page.getByText("Revoked")).toBeVisible();

  // The recruiter gate re-checks the link on every read, so the now-revoked
  // session is sent back to the landing page.
  const blockedPage = await visitor.newPage();
  await blockedPage.goto("/portfolio");
  // The gate sends the revoked session to the landing page (origin root).
  await expect(blockedPage).toHaveURL(/^http:\/\/localhost:\d+\/$/);

  await visitor.close();
});
