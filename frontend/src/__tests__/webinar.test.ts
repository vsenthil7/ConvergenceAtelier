import { describe, it, expect, vi } from "vitest";
import {
  webinarStatus,
  webinarRegister,
  webinarCancel,
  webinarWaitlist,
  webinarReminders,
} from "../lib/webinar";

function fetchReturning(status: number, body: unknown, ok = status < 400): typeof fetch {
  return vi.fn(async () => ({ ok, status, json: async () => body })) as unknown as typeof fetch;
}

const statusBody = {
  event_id: "e1",
  capacity: 2,
  registered_count: 1,
  waitlisted_count: 0,
  seats_left: 1,
  my_state: "registered",
  stream_url: "https://s/x",
};

describe("webinar api client", () => {
  it("fetches status (functional)", async () => {
    const f = fetchReturning(200, statusBody);
    const out = await webinarStatus("e1", f);
    expect(out.capacity).toBe(2);
    expect(out.my_state).toBe("registered");
  });

  it("registers (functional)", async () => {
    const spy = vi.fn(async () => ({
      ok: true,
      status: 201,
      json: async () => ({ event_id: "e1", status: "registered" }),
    }));
    const out = await webinarRegister("e1", spy as unknown as typeof fetch);
    expect(out.status).toBe("registered");
    expect(spy.mock.calls[0][0]).toContain("/api/events/e1/webinar/register");
    expect((spy.mock.calls[0][1] as RequestInit).method).toBe("POST");
  });

  it("cancels (functional)", async () => {
    const spy = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({ event_id: "e1", status: "cancelled" }),
    }));
    const out = await webinarCancel("e1", spy as unknown as typeof fetch);
    expect(out.status).toBe("cancelled");
    expect((spy.mock.calls[0][1] as RequestInit).method).toBe("DELETE");
  });

  it("fetches the waitlist (functional)", async () => {
    const f = fetchReturning(200, [
      { user_id: "u1", email: "a@x.com", full_name: "A", position: 1 },
    ]);
    const out = await webinarWaitlist("e1", f);
    expect(out[0].position).toBe(1);
  });

  it("fetches reminders (functional)", async () => {
    const f = fetchReturning(200, [
      { offset: "24h", send_at: "2026-06-30T17:00:00+00:00" },
      { offset: "1h", send_at: "2026-07-01T16:00:00+00:00" },
    ]);
    const out = await webinarReminders("e1", f);
    expect(out.map((r) => r.offset)).toEqual(["24h", "1h"]);
  });

  it("throws API detail on error (negative)", async () => {
    const f = fetchReturning(403, { detail: "Only admins can view the waitlist" }, false);
    await expect(webinarWaitlist("e1", f)).rejects.toThrow("Only admins can view the waitlist");
  });

  it("falls back to status message on non-JSON error (negative)", async () => {
    const f = vi.fn(async () => ({
      ok: false,
      status: 500,
      json: async () => {
        throw new Error("not json");
      },
    })) as unknown as typeof fetch;
    await expect(webinarStatus("e1", f)).rejects.toThrow("Request failed: 500");
  });
});
