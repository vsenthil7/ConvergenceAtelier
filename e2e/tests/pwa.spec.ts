import { test, expect } from "@playwright/test";

// PWA: the web manifest is served and declares the installable app identity.
test("serves a valid PWA manifest", async ({ page, request }) => {
  await page.goto("/");
  const href = await page.getAttribute('link[rel="manifest"]', "href");
  expect(href).toBeTruthy();
  const resp = await request.get(href!);
  expect(resp.ok()).toBeTruthy();
  const manifest = await resp.json();
  expect(manifest.name).toBe("Convergence Atelier");
  expect(manifest.display).toBe("standalone");
});
