/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

// Convergence Atelier frontend build config.
// PWA: installable shell + offline caching so the attendee app works on mobile.
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      manifest: {
        name: "Convergence Atelier",
        short_name: "Atelier",
        description: "All-in-one conference organiser platform",
        theme_color: "#0b1f3a",
        background_color: "#0b1f3a",
        display: "standalone",
        start_url: "/",
        icons: [
          { src: "icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "icon-512.png", sizes: "512x512", type: "image/png" },
        ],
      },
    }),
  ],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://localhost:8096", changeOrigin: true },
    },
  },
  preview: { port: 8095 },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test-setup.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov"],
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/main.tsx",
        "src/**/*.test.ts",
        "src/**/*.test.tsx",
        "src/test-setup.ts",
        "src/vite-env.d.ts",
      ],
      // Statements + lines are held at 100% (every line must execute under test).
      // Branch/function thresholds sit a touch below 100% only because v8 counts
      // each inline JSX arrow (Kendo component onChange handlers, one-shot .map
      // callbacks) as a separate "function"/"branch"; several of those cannot be
      // driven through jsdom (the Grid/DropDownList render in portals with zero
      // layout). Every hand-written code path is covered; these floors prevent
      // real regressions without forcing brittle framework-internal tests.
      thresholds: { lines: 100, statements: 100, branches: 95, functions: 88 },
    },
  },
});
