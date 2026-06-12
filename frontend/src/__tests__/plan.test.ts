import { describe, it, expect, vi } from "vitest";
import { draftPlan } from "../lib/plan";

const planRows = [
  { order: 0, key: "registration", label: "Open registration", detail: "x", target_at: "2026-07-01T09:00:00+00:00", relevance: 0.1 },
  { order: 1, key: "judging", label: "Judging & scoring", detail: "y", target_at: "2026-07-03T09:00:00+00:00", relevance: 0.8 },
];

describe("plan api client", () => {
  it("drafts a plan and sends the theme (functional)", async () => {
    const spy = vi.fn(async () => ({ ok: true, status: 200, json: async () => planRows }));
    const out = await draftPlan("e1", "judging", spy as unknown as typeof fetch);
    expect(out).toHaveLength(2);
    expect(out[1].key).toBe("judging");
    expect(spy.mock.calls[0][0]).toContain("/api/discovery/events/e1/plan");
    expect(JSON.parse(String((spy.mock.calls[0][1] as RequestInit).body)).theme).toBe("judging");
  });

  it("throws API detail on error (negative)", async () => {
    const f = vi.fn(async () => ({
      ok: false,
      status: 404,
      json: async () => ({ detail: "Event not found" }),
    })) as unknown as typeof fetch;
    await expect(draftPlan("missing", "x", f)).rejects.toThrow("Event not found");
  });

  it("falls back to status message on non-JSON error (negative)", async () => {
    const f = vi.fn(async () => ({
      ok: false,
      status: 500,
      json: async () => {
        throw new Error("not json");
      },
    })) as unknown as typeof fetch;
    await expect(draftPlan("e1", "x", f)).rejects.toThrow("Request failed: 500");
  });
});
