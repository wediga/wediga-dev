import { test, expect } from "@playwright/test";
import { login, PNG_BYTES } from "../helpers";

const CROP = { x: 30, y: 20, zoom: 150 };

// The suite shares one database and runs its files one after the other in
// name order, so this file runs before portrait-admin.spec.ts and starts
// without a portrait. The quiet landing renders without WebGL, so the
// portrait is in the visible page and not only on a planet of the ride.
test("the landing shows the portrait only once one is uploaded, with its crop", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.locator('img[src="/api/portrait"]')).toHaveCount(0);

  await login(page);
  const csrf = (await (await page.request.get("/api/csrf")).json()).csrf_token;
  const headers = { "X-CSRF-Token": csrf };
  const uploaded = await page.request.post("/api/portrait", {
    headers,
    multipart: {
      file: { name: "portrait.png", mimeType: "image/png", buffer: PNG_BYTES },
    },
  });
  expect(uploaded.status()).toBe(201);
  expect((await page.request.put("/api/portrait/crop", { headers, data: CROP })).status()).toBe(200);

  await page.goto("/");
  const portrait = page.locator('img[src="/api/portrait"]');
  await expect(portrait).toBeVisible();
  await expect(portrait).toHaveCSS("object-position", "30% 20%");
  await expect(portrait).toHaveCSS("transform", "matrix(1.5, 0, 0, 1.5, 0, 0)");
});
