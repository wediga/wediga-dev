import { test, expect } from "@playwright/test";
import { login } from "../helpers";

// A minimal valid PDF: the %PDF signature is what the backend upload check
// looks for. It carries no personal data.
const PDF_BYTES = Buffer.from("%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n");

// The new CV flow: the admin uploads a PDF and the gated download serves back
// exactly that PDF. An admin session satisfies the recruiter gate, so logging
// in is enough to reach the download. The upload and the download go through
// the BFF route handlers, not the JSON proxy, just as in production.
test("the admin uploads a PDF and the download returns exactly that PDF", async ({
  page,
}) => {
  await login(page);

  await page.goto("/admin/cv");
  await expect(page.getByText("No CV uploaded yet.")).toBeVisible();

  const uploaded = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/cv") &&
      response.request().method() === "POST",
  );
  await page.locator('input[type="file"]').setInputFiles({
    name: "cv.pdf",
    mimeType: "application/pdf",
    buffer: PDF_BYTES,
  });
  expect((await uploaded).status()).toBe(201);
  await expect(page.getByText("CV uploaded")).toBeVisible();

  const response = await page.request.get("/api/cv/download");
  expect(response.status()).toBe(200);
  expect(response.headers()["content-type"]).toContain("application/pdf");
  const body = await response.body();
  expect(body.equals(PDF_BYTES)).toBe(true);
});
