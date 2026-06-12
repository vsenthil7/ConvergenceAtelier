import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { App } from "../App";

function mockFetch(handler: (url: string, init?: RequestInit) => unknown): typeof fetch {
  return vi.fn(async (url: string, init?: RequestInit) => {
    const body = handler(url, init);
    return { ok: true, status: 200, json: async () => body };
  }) as unknown as typeof fetch;
}

describe("App shell (S1)", () => {
  it("shows health ok and the events view (functional)", async () => {
    const f = mockFetch((url) => {
      if (url.includes("/api/health")) {
        return { status: "ok", service: "Convergence Atelier", version: "0.1.0", mode: "mock", time: "t" };
      }
      return []; // events list
    });
    render(<App fetchImpl={f} />);
    await waitFor(() => expect(screen.getByTestId("health-ok")).toBeInTheDocument());
    expect(screen.getByText("Events")).toBeInTheDocument();
  });

  it("shows backend offline when health fails (negative)", async () => {
    const f = vi.fn(async (url: string) => {
      if (url.includes("/api/health")) {
        return { ok: false, status: 500, json: async () => ({}) };
      }
      return { ok: true, status: 200, json: async () => [] };
    }) as unknown as typeof fetch;
    render(<App fetchImpl={f} />);
    await waitFor(() => expect(screen.getByTestId("health-error")).toBeInTheDocument());
  });
});
