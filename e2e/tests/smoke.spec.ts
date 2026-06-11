import { test, expect } from "@playwright/test";

// Smoke: the app shell loads and shows the brand on desktop and mobile.
test("app shell renders brand", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Convergence Atelier")).toBeVisible();
});
