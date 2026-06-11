import { defineConfig, devices } from "@playwright/test";

// E2E runs against the built frontend preview (port 8095) with the backend (8096).
// The webServer block boots both so CI and local runs are one command.
const BASE_URL = process.env.E2E_BASE_URL ?? "http://localhost:8095";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: [["html", { open: "never" }], ["list"]],
  use: {
    baseURL: BASE_URL,
    trace: "on-first-retry",
  },
  projects: [
    { name: "desktop-chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile-safari", use: { ...devices["iPhone 13"] } },
  ],
  // When E2E_EXTERNAL is set, assume servers are already up (e.g. against the VPS).
  webServer: process.env.E2E_EXTERNAL
    ? undefined
    : {
        command: "npm --prefix ../frontend run preview",
        url: BASE_URL,
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
});
