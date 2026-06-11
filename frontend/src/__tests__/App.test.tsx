import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { App } from "../App";
import type { HealthStatus } from "../lib/api";

const okHealth: HealthStatus = {
  status: "ok",
  service: "Convergence Atelier",
  version: "0.1.0",
  mode: "mock",
  time: "2026-06-12T00:00:00+00:00",
};

function mockFetch(impl: () => Promise<Response>): typeof fetch {
  return vi.fn(impl) as unknown as typeof fetch;
}

describe("App shell", () => {
  it("renders the brand and loads health (functional)", async () => {
    const f = mockFetch(async () => new Response(JSON.stringify(okHealth), { status: 200 }));
    render(<App fetchImpl={f} />);
    expect(screen.getByText("Convergence Atelier")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId("health-ok")).toBeInTheDocument());
    expect(screen.getByText("Mode: mock")).toBeInTheDocument();
  });

  it("shows an error when the backend is unreachable (negative)", async () => {
    const f = mockFetch(async () => new Response("nope", { status: 500 }));
    render(<App fetchImpl={f} />);
    await waitFor(() => expect(screen.getByTestId("health-error")).toBeInTheDocument());
  });

  it("handles a thrown network error (negative)", async () => {
    const f = mockFetch(async () => {
      throw new Error("network down");
    });
    render(<App fetchImpl={f} />);
    await waitFor(() => expect(screen.getByTestId("health-error")).toHaveTextContent("network down"));
  });

  it("handles a non-Error rejection (negative branch)", async () => {
    const f = mockFetch(() => Promise.reject("string failure"));
    render(<App fetchImpl={f} />);
    await waitFor(() => expect(screen.getByTestId("health-error")).toHaveTextContent("Unknown error"));
  });

  it("re-checks health when Refresh is clicked (functional)", async () => {
    let calls = 0;
    const f = mockFetch(async () => {
      calls += 1;
      return new Response(JSON.stringify(okHealth), { status: 200 });
    });
    render(<App fetchImpl={f} />);
    await waitFor(() => expect(screen.getByTestId("health-ok")).toBeInTheDocument());
    await userEvent.click(screen.getByText("Refresh status"));
    await waitFor(() => expect(calls).toBeGreaterThanOrEqual(2));
  });
});
