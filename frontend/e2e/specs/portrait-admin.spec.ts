import { test, expect } from "@playwright/test";
import { login, PNG_BYTES } from "../helpers";

// The admin uploads a portrait, moves its focus with the arrow keys, zooms in
// and saves, and the backend keeps exactly that crop. The upload goes through
// the BFF route handler, as in production.
test("the admin uploads a portrait and saves its crop", async ({ page }) => {
  await login(page);
  await page.goto("/admin/profile");

  await page.locator('input[type="file"]').setInputFiles({
    name: "portrait.png",
    mimeType: "image/png",
    buffer: PNG_BYTES,
  });
  await expect(page.getByText("Portrait uploaded")).toBeVisible();

  await page.getByRole("button", { name: /Portrait focus/ }).press("ArrowLeft");
  await page.getByRole("slider").fill("150");
  await page.getByRole("button", { name: "Save crop" }).click();
  await expect(page.getByText("Crop saved")).toBeVisible();

  const crop = await page.request.get("/api/portrait/crop");
  expect(await crop.json()).toEqual({ x: 52, y: 50, zoom: 150 });

  const image = await page.request.get("/api/portrait");
  expect(image.headers()["content-type"]).toBe("image/png");
  expect((await image.body()).equals(PNG_BYTES)).toBe(true);
});
