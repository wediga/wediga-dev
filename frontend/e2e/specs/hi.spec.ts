import { test, expect } from "@playwright/test";
import { login, openAdminPage } from "../helpers";

const PHONE = "+49 151 2345-678";
const WEBSITE = "https://example.com";

// The page behind the QR code: the admin adds a phone number and a website to
// the profile, and /hi offers every way of contact plus the vCard, while
// search engines are asked to leave it out.
test("/hi shows the contact card with its links and the vCard", async ({ page }) => {
  await login(page);
  await openAdminPage(page, "/admin/profile");
  await page.getByRole("textbox", { name: "Phone" }).fill(PHONE);
  await page.getByRole("textbox", { name: "Website" }).fill(WEBSITE);
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByText("Saved")).toBeVisible();

  await page.goto("/hi");
  const name = await page.getByRole("heading", { level: 1 }).textContent();
  const contact = page.getByRole("navigation", { name: "Kontakt" });
  await expect(contact.getByRole("link", { name: "Anrufen" })).toHaveAttribute(
    "href",
    "tel:+491512345678",
  );
  await expect(contact.getByRole("link", { name: "E-Mail schreiben" })).toHaveAttribute(
    "href",
    /^mailto:/,
  );
  await expect(contact.getByRole("link", { name: "Website" })).toHaveAttribute("href", WEBSITE);
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", /noindex/);

  const download = page.waitForEvent("download");
  await contact.getByRole("link", { name: "Kontakt speichern" }).click();
  const vcard = await download;
  expect(vcard.suggestedFilename()).toBe("Kontakt.vcf");

  const text = await (await page.request.get("/api/card/vcard")).text();
  expect(text).toContain(`FN:${name}`);
  expect(text).toContain(`TEL;TYPE=CELL:${PHONE}`);
  expect(text).toContain(`URL:${WEBSITE}`);
});
