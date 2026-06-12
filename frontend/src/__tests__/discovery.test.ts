import { describe, it, expect, vi } from "vitest";
import {
  matchAttendees,
  recommendForInterests,
  similarSessions,
} from "../lib/discovery";

function fetchReturning(status: number, body: unknown, ok = status < 400): typeof fetch {
  return vi.fn(async () => ({ ok, status, json: async () => body })) as unknown as typeof fetch;
}

const SESSION = {
  id: "s1",
  event_id: "e1",
  title: "React hooks",
  track: "Frontend",
  speaker: "Ada",
  starts_at: "2026-06-11T10:00:00.000Z",
  ends_at: "2026-06-11T11:00:00.000Z",
};

describe("discovery api client", () => {
  it("fetches similar sessions with the limit in the query (functional)", async () => {
    const spy = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => [{ score: 0.9, session: SESSION }],
    }));
    const out = await similarSessions("s1", 3, spy as unknown as typeof fetch);
    expect(out[0].score).toBe(0.9);
    expect(spy.mock.calls[0][0]).toContain("/api/discovery/sessions/s1/similar?limit=3");
  });

  it("posts interests to the recommend endpoint (functional)", async () => {
    const spy = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => [{ score: 0.5, session: SESSION }],
    }));
    const out = await recommendForInterests("react", 5, spy as unknown as typeof fetch);
    expect(out).toHaveLength(1);
    const init = spy.mock.calls[0][1] as RequestInit;
    expect(JSON.parse(String(init.body))).toEqual({ interests: "react", limit: 5 });
  });

  it("posts attendees to the match endpoint (functional)", async () => {
    const spy = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => [{ score: 0.8, a: { id: "1", name: "A" }, b: { id: "2", name: "B" } }],
    }));
    const out = await matchAttendees(
      [
        { id: "1", name: "A", interests: "react" },
        { id: "2", name: "B", interests: "react" },
      ],
      5,
      spy as unknown as typeof fetch,
    );
    expect(out[0].a.id).toBe("1");
  });

  it("throws API detail with status on error (negative)", async () => {
    const f = fetchReturning(404, { detail: "Session not found" }, false);
    await expect(similarSessions("nope", 5, f)).rejects.toThrow("Session not found");
  });

  it("falls back to status message on non-JSON error (negative)", async () => {
    const f = vi.fn(async () => ({
      ok: false,
      status: 500,
      json: async () => {
        throw new Error("not json");
      },
    })) as unknown as typeof fetch;
    await expect(recommendForInterests("x", 5, f)).rejects.toThrow("Request failed: 500");
  });

  it("attaches the status code to the thrown error (negative)", async () => {
    const f = fetchReturning(403, { detail: "Forbidden" }, false);
    await expect(matchAttendees([{ id: "1" }, { id: "2" }], 5, f)).rejects.toMatchObject({
      status: 403,
    });
  });
});
