import { test, expect } from "@playwright/test";
import { login, openAdminPage } from "../helpers";

// An admin edit must reach the public view. Since Phase H2 the public landing
// carries skills (the full About story moved behind the recruiter login), so a
// new skill is the cleanest public propagation probe: it proves the edit went
// through the full BFF-to-backend write path and back out through a public,
// uncached read. Skills are read without a session, exactly like About was.
test("a new skill in the admin appears on the public landing page", async ({
  page,
}) => {
  await login(page);

  await openAdminPage(page, "/admin/skills");
  await expect(page.getByRole("heading", { name: "Skills" })).toBeVisible();

  // Add a uniquely-marked technology to the first seeded category and wait for
  // the write to land, so the public read below cannot race ahead of the commit.
  const stamp = Date.now();
  const marker = `E2E skill marker ${stamp}`;
  await page.getByLabel("New technology name").first().fill(marker);
  await page
    .getByLabel("New technology topic")
    .first()
    .fill(`e2e-marker-${stamp}`);
  const written = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      response.url().endsWith("/api/content/technologies") &&
      response.ok(),
  );
  await page.getByRole("button", { name: "Add technology" }).first().click();
  await written;

  // The public landing page reads skills without a session and must show it.
  // Reduced motion renders the flat readable column, so the skill appears once
  // (not duplicated by the visible station overlay) and needs no WebGL.
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await expect(page.getByText(marker)).toBeVisible();
});
