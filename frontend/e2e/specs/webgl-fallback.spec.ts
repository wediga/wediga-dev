import { test, expect } from "@playwright/test";

// A browser that refuses a WebGL context (hardware acceleration off, remote
// desktop, blocked driver) must still get a readable landing. The default
// desktop viewport starts in full motion, so this covers the ride falling back
// to the quiet column without the sun, with a note and a locked switch.
test("the landing falls back to the quiet view when WebGL is unavailable", async ({
  page,
}) => {
  // Refuse every WebGL context before any page script runs, the way such a
  // browser does.
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    Object.defineProperty(HTMLCanvasElement.prototype, "getContext", {
      value(this: HTMLCanvasElement, type: string, ...args: unknown[]) {
        return type.includes("webgl")
          ? null
          : Reflect.apply(original, this, [type, ...args]);
      },
    });
  });

  await page.goto("/");

  await expect(
    page.getByText("Dein Browser kann die Animation gerade nicht darstellen"),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { level: 1, name: "Alexander Wedig" }),
  ).toBeVisible();
  await expect(page.locator("canvas")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Voll" })).toBeDisabled();
});
