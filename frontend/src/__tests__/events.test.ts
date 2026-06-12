import { describe, it, expect, vi } from "vitest";
import {
  listEvents,
  createEvent,
  updateEvent,
  deleteEvent,
  addSession,
  registerForEvent,
  cancelRegistration,
  myRegistration,
  eventParticipants,
  type EventModel,
} from "../lib/events";

const sampleEvent: EventModel = {
  id: "e1",
  name: "React Summit",
  location: "Amsterdam",
  description: "",
  event_type: "conference",
  config: {},
  starts_at: "2026-06-11T09:00:00+00:00",
  ends_at: "2026-06-12T17:00:00+00:00",
  sessions: [],
};

function fetchReturning(status: number, body: unknown, ok = status < 400): typeof fetch {
  return vi.fn(async () => ({
    ok,
    status,
    json: async () => body,
  })) as unknown as typeof fetch;
}

describe("events api client", () => {
  it("lists events (functional)", async () => {
    const f = fetchReturning(200, [sampleEvent]);
    const result = await listEvents(f);
    expect(result).toHaveLength(1);
    expect(result[0].name).toBe("React Summit");
  });

  it("creates an event (functional)", async () => {
    const f = fetchReturning(201, sampleEvent);
    const result = await createEvent(
      {
        name: "React Summit",
        location: "Amsterdam",
        description: "",
        event_type: "conference",
        starts_at: sampleEvent.starts_at,
        ends_at: sampleEvent.ends_at,
      },
      f,
    );
    expect(result.id).toBe("e1");
  });

  it("updates an event (functional)", async () => {
    const f = fetchReturning(200, { ...sampleEvent, name: "JSNation" });
    const result = await updateEvent("e1", { name: "JSNation" }, f);
    expect(result.name).toBe("JSNation");
  });

  it("deletes an event with no body (functional)", async () => {
    const f = fetchReturning(204, null);
    await expect(deleteEvent("e1", f)).resolves.toBeUndefined();
  });

  it("adds a session (functional)", async () => {
    const session = {
      id: "s1",
      event_id: "e1",
      title: "Keynote",
      track: "Main",
      speaker: "Jane",
      starts_at: "2026-06-11T10:00:00+00:00",
      ends_at: "2026-06-11T11:00:00+00:00",
    };
    const f = fetchReturning(201, session);
    const result = await addSession("e1", {
      title: "Keynote",
      track: "Main",
      speaker: "Jane",
      starts_at: session.starts_at,
      ends_at: session.ends_at,
    }, f);
    expect(result.title).toBe("Keynote");
  });

  it("throws API detail on error (negative)", async () => {
    const f = fetchReturning(404, { detail: "Event nope not found" }, false);
    await expect(listEvents(f)).rejects.toThrow("Event nope not found");
  });

  it("falls back to status message on non-JSON error (negative)", async () => {
    const f = vi.fn(async () => ({
      ok: false,
      status: 500,
      json: async () => {
        throw new Error("not json");
      },
    })) as unknown as typeof fetch;
    await expect(listEvents(f)).rejects.toThrow("Request failed: 500");
  });

  it("falls back when error body lacks a string detail (negative)", async () => {
    const f = fetchReturning(422, { detail: [{ msg: "bad" }] }, false);
    await expect(createEvent(
      { name: "", location: "", description: "", event_type: "conference", starts_at: "", ends_at: "" },
      f,
    )).rejects.toThrow("Request failed: 422");
  });

  it("registers for an event (functional)", async () => {
    const spy = vi.fn(async () => ({ ok: true, status: 201, json: async () => ({ status: "registered" }) }));
    const out = await registerForEvent("e1", spy as unknown as typeof fetch);
    expect(out.status).toBe("registered");
    expect(spy.mock.calls[0][0]).toContain("/api/events/e1/register");
    expect((spy.mock.calls[0][1] as RequestInit).method).toBe("POST");
  });

  it("cancels a registration (functional)", async () => {
    const spy = vi.fn(async () => ({ ok: true, status: 200, json: async () => ({ status: "cancelled" }) }));
    const out = await cancelRegistration("e1", spy as unknown as typeof fetch);
    expect(out.status).toBe("cancelled");
    expect((spy.mock.calls[0][1] as RequestInit).method).toBe("DELETE");
  });

  it("reads my registration status (functional)", async () => {
    const f = fetchReturning(200, { event_id: "e1", status: "registered" });
    const out = await myRegistration("e1", f);
    expect(out.status).toBe("registered");
  });

  it("lists event participants (functional)", async () => {
    const f = fetchReturning(200, [
      { user_id: "u1", email: "a@x.com", full_name: "A", status: "registered" },
    ]);
    const out = await eventParticipants("e1", f);
    expect(out).toHaveLength(1);
    expect(out[0].email).toBe("a@x.com");
  });

  it("propagates a 404 when registering for an out-of-scope event (negative)", async () => {
    const f = fetchReturning(404, { detail: "Event not found" }, false);
    await expect(registerForEvent("missing", f)).rejects.toThrow("Event not found");
  });
});
