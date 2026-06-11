import { test, expect } from "@playwright/test";

// Functional: with the API reachable, the status card shows ok + mode.
test("health status loads and shows mode", async ({ page }) => {
  await page.route("**/api/health", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "ok",
        service: "Convergence Atelier",
        version: "0.1.0",
        mode: "mock",
        time: "2026-06-12T00:00:00+00:00",
      }),
    }),
  );
  await page.goto("/");
  await expect(page.getByTestId("health-ok")).toBeVisible();
  await expect(page.getByText("Mode: mock")).toBeVisible();
});

// Negative: when the API errors, the shell shows a clear, non-crashing message.
test("health failure shows error state", async ({ page }) => {
  await page.route("**/api/health", (route) => route.fulfill({ status: 500, body: "down" }));
  await page.goto("/");
  await expect(page.getByTestId("health-error")).toBeVisible();
});
