import { test, expect } from "@playwright/test";

// Shared API stubs so the SPA can boot to a known auth state.
async function stubAuth(page, role = "tenant_admin") {
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
        role,
        tenant_id: "t1",
        auth_provider: "local",
        last_login_at: null,
      }),
    }),
  );
  await page.route("**/api/events", (r) =>
    r.fulfill({ status: 200, contentType: "application/json", body: "[]" }),
  );
  await page.route("**/api/auth/users", (r) =>
    r.fulfill({ status: 200, contentType: "application/json", body: "[]" }),
  );
}

// Functional: the login screen renders for an unauthenticated visitor.
test("login screen renders for anonymous visitor", async ({ page }) => {
  await stubAuth(page);
  await page.goto("/");
  await expect(page.getByTestId("login-submit")).toBeVisible();
  await expect(page.getByText(/Demo accounts/)).toBeVisible();
});

// Functional: signing in reveals the role-aware shell.
test("password sign-in reveals the events workspace", async ({ page }) => {
  await stubAuth(page, "tenant_admin");
  await page.goto("/");
  await page.getByLabel("login-email").fill("admin@react-summit.demo");
  await page.getByLabel("login-password").fill("Atelier!2026");
  await page.getByTestId("login-submit").click();
  await expect(page.getByTestId("whoami")).toBeVisible();
  await expect(page.getByTestId("nav-users")).toBeVisible();
});

// Role-aware negative: an attendee does not see the Users tab.
test("attendee role hides the Users tab", async ({ page }) => {
  await stubAuth(page, "user");
  await page.goto("/");
  await page.getByLabel("login-email").fill("user@react-summit.demo");
  await page.getByLabel("login-password").fill("Atelier!2026");
  await page.getByTestId("login-submit").click();
  await expect(page.getByTestId("nav-events")).toBeVisible();
  await expect(page.getByTestId("nav-users")).toHaveCount(0);
});
