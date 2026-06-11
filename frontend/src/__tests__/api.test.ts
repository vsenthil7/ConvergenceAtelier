import { describe, it, expect, vi } from "vitest";
import { getHealth } from "../lib/api";

function mockFetch(status: number, body: unknown): typeof fetch {
  return vi.fn(
    async () => new Response(JSON.stringify(body), { status }),
  ) as unknown as typeof fetch;
}

describe("api.getHealth", () => {
  it("returns parsed health on 200 (functional)", async () => {
    const payload = { status: "ok", service: "Convergence Atelier", version: "0.1.0", mode: "mock", time: "t" };
    const data = await getHealth(mockFetch(200, payload));
    expect(data.status).toBe("ok");
    expect(data.mode).toBe("mock");
  });

  it("throws on non-2xx (negative)", async () => {
    await expect(getHealth(mockFetch(503, {}))).rejects.toThrow("Health check failed: 503");
  });
});
