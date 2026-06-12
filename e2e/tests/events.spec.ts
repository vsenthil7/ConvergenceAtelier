import { test, expect } from "@playwright/test";

// Functional: events list renders in the grid, agenda shows for the first event.
test("events grid and agenda render", async ({ page }) => {
  await page.route("**/api/health", (r) =>
    r.fulfill({
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
    r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "e1",
          name: "React Summit",
          location: "Amsterdam",
          description: "",
          starts_at: "2026-06-11T09:00:00+00:00",
          ends_at: "2026-06-12T17:00:00+00:00",
          sessions: [
            {
              id: "s1",
              event_id: "e1",
              title: "Keynote",
              track: "Main",
              speaker: "Jane",
              starts_at: "2026-06-11T10:00:00+00:00",
              ends_at: "2026-06-11T11:00:00+00:00",
            },
          ],
        },
      ]),
    }),
  );

  await page.goto("/");
  await expect(page.getByTestId("events-grid")).toBeVisible();
  await expect(page.getByText("React Summit")).toBeVisible();
  await expect(page.getByTestId("agenda")).toBeVisible();
});

// Negative: when the events API errors, the view shows an error, not a crash.
test("events error state shows on API failure", async ({ page }) => {
  await page.route("**/api/health", (r) =>
    r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "ok", service: "x", version: "0", mode: "mock", time: "t" }),
    }),
  );
  await page.route("**/api/events", (r) =>
    r.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "boom" }) }),
  );

  await page.goto("/");
  await expect(page.getByTestId("events-error")).toBeVisible();
});

// Functional: empty state when there are no events.
test("empty state renders with no events", async ({ page }) => {
  await page.route("**/api/health", (r) =>
    r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "ok", service: "x", version: "0", mode: "mock", time: "t" }),
    }),
  );
  await page.route("**/api/events", (r) =>
    r.fulfill({ status: 200, contentType: "application/json", body: "[]" }),
  );

  await page.goto("/");
  await expect(page.getByTestId("events-empty")).toBeVisible();
});
