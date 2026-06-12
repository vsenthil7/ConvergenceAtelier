import { test, expect } from "@playwright/test";

// Functional: with the API reachable, the AppBar shows the service + mode.
test("health status shows service and mode in the app bar", async ({ page }) => {
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
  await page.route("**/api/events", (r) =>
    r.fulfill({ status: 200, contentType: "application/json", body: "[]" }),
  );
  await page.goto("/");
  await expect(page.getByTestId("health-ok")).toBeVisible();
  await expect(page.getByText(/mock/)).toBeVisible();
});

// Negative: when the health API errors, the bar shows backend offline (no crash).
test("health failure shows offline indicator", async ({ page }) => {
  await page.route("**/api/health", (route) => route.fulfill({ status: 500, body: "down" }));
  await page.route("**/api/events", (r) =>
    r.fulfill({ status: 200, contentType: "application/json", body: "[]" }),
  );
  await page.goto("/");
  await expect(page.getByTestId("health-error")).toBeVisible();
});
