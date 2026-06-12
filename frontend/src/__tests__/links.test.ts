import { describe, it, expect, vi } from "vitest";
import { listLinks, linkEvent, unlinkEvent, combinedCatalog } from "../lib/links";

function fetchReturning(status: number, body: unknown, ok = status < 400): typeof fetch {
  return vi.fn(async () => ({ ok, status, json: async () => body })) as unknown as typeof fetch;
}

const linked = {
  id: "e2",
  name: "Online",
  location: "Online",
  event_type: "hybrid",
  starts_at: "2026-07-01T09:00:00+00:00",
  ends_at: "2026-07-01T17:00:00+00:00",
};

const catalogRow = {
  session_id: "s1",
  event_id: "e1",
  event_name: "Flagship",
  title: "Keynote",
  track: "Main",
  speaker: "Jane",
  mode: "hybrid",
  stream_url: "",
  recording_url: "",
  starts_at: "2026-07-01T10:00:00+00:00",
};

describe("links api client", () => {
  it("lists links (functional)", async () => {
    const f = fetchReturning(200, [linked]);
    const out = await listLinks("e1", f);
    expect(out[0].id).toBe("e2");
  });

  it("links an event and sends the other id (functional)", async () => {
    const spy = vi.fn(async () => ({ ok: true, status: 201, json: async () => [linked] }));
    const out = await linkEvent("e1", "e2", spy as unknown as typeof fetch);
    expect(out).toHaveLength(1);
    expect(spy.mock.calls[0][0]).toContain("/api/events/e1/links");
    expect(JSON.parse(String((spy.mock.calls[0][1] as RequestInit).body)).other_event_id).toBe("e2");
  });

  it("unlinks an event (functional)", async () => {
    const spy = vi.fn(async () => ({ ok: true, status: 200, json: async () => [] }));
    const out = await unlinkEvent("e1", "e2", spy as unknown as typeof fetch);
    expect(out).toEqual([]);
    expect(spy.mock.calls[0][0]).toContain("/api/events/e1/links/e2");
    expect((spy.mock.calls[0][1] as RequestInit).method).toBe("DELETE");
  });

  it("fetches the combined catalog (functional)", async () => {
    const f = fetchReturning(200, [catalogRow]);
    const out = await combinedCatalog("e1", f);
    expect(out[0].event_name).toBe("Flagship");
  });

  it("throws API detail on error (negative)", async () => {
    const f = fetchReturning(409, { detail: "cannot link an event to itself" }, false);
    await expect(linkEvent("e1", "e1", f)).rejects.toThrow("cannot link an event to itself");
  });

  it("falls back to status message on non-JSON error (negative)", async () => {
    const f = vi.fn(async () => ({
      ok: false,
      status: 500,
      json: async () => {
        throw new Error("not json");
      },
    })) as unknown as typeof fetch;
    await expect(listLinks("e1", f)).rejects.toThrow("Request failed: 500");
  });
});
