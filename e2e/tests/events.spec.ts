import { test, expect } from "@playwright/test";

// Sign-in helper: stub auth so each test starts authenticated as an admin.
async function signIn(page, eventsBody: string, eventsStatus = 200) {
  await page.route("**/api/auth/config", (r) =>
    r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ google_enabled: false, google_client_id: "" }),
    }),
  );
  await page.route("**/api/auth/login", (r) =>
    r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ access_token: "tok", token_type: "bearer" }),
    }),
  );
  await page.route("**/api/auth/me", (r) =>
    r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "u1",
        email: "admin@react-summit.demo",
        full_name: "Admin",
        role: "tenant_admin",
        tenant_id: "t1",
        auth_provider: "local",
        last_login_at: null,
      }),
    }),
  );
  await page.route("**/api/events", (r) =>
    r.fulfill({ status: eventsStatus, contentType: "application/json", body: eventsBody }),
  );

  await page.goto("/");
  await page.getByLabel("login-email").fill("admin@react-summit.demo");
  await page.getByLabel("login-password").fill("Atelier!2026");
  await page.getByTestId("login-submit").click();
  await expect(page.getByTestId("whoami")).toBeVisible();
}

const ONE_EVENT = JSON.stringify([
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
]);

// Functional: events grid + agenda render after sign-in.
test("events grid and agenda render", async ({ page }) => {
  await signIn(page, ONE_EVENT);
  await expect(page.getByTestId("events-grid")).toBeVisible();
  await expect(page.getByText("React Summit")).toBeVisible();
  await expect(page.getByTestId("agenda")).toBeVisible();
});

// Negative: events API error shows the error state, not a crash.
test("events error state shows on API failure", async ({ page }) => {
  await signIn(page, JSON.stringify({ detail: "boom" }), 500);
  await expect(page.getByTestId("events-error")).toBeVisible();
});

// Functional: empty state when there are no events.
test("empty state renders with no events", async ({ page }) => {
  await signIn(page, "[]");
  await expect(page.getByTestId("events-empty")).toBeVisible();
});
