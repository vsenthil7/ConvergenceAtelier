import { describe, it, expect, vi } from "vitest";
import { makeAuthedFetch } from "../lib/authedFetch";

describe("makeAuthedFetch", () => {
  it("adds the bearer header when a token is present (functional)", async () => {
    const base = vi.fn(async () => ({ ok: true, status: 200, json: async () => ({}) }));
    const authed = makeAuthedFetch("tok", base as unknown as typeof fetch);
    await authed("/api/events");
    const init = base.mock.calls[0][1] as RequestInit;
    expect((init.headers as Headers).get("Authorization")).toBe("Bearer tok");
  });

  it("omits the header when there is no token (negative)", async () => {
    const base = vi.fn(async () => ({ ok: true, status: 200, json: async () => ({}) }));
    const authed = makeAuthedFetch(null, base as unknown as typeof fetch);
    await authed("/api/events");
    const init = base.mock.calls[0][1] as RequestInit;
    expect((init.headers as Headers).get("Authorization")).toBeNull();
  });

  it("preserves existing init options (functional)", async () => {
    const base = vi.fn(async () => ({ ok: true, status: 200, json: async () => ({}) }));
    const authed = makeAuthedFetch("tok", base as unknown as typeof fetch);
    await authed("/api/events", { method: "POST", body: "{}" });
    const init = base.mock.calls[0][1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(init.body).toBe("{}");
  });
});
