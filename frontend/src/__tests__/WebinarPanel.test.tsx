import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { WebinarPanel } from "../components/WebinarPanel";

const reminders = [
  { offset: "24h", send_at: "2026-06-30T17:00:00+00:00" },
  { offset: "1h", send_at: "2026-07-01T16:00:00+00:00" },
];

/** Mutable mock store so join/leave reflect in subsequent status reads. */
function makeFetch(opts: {
  capacity?: number;
  seatsLeft?: number | null;
  myState?: "registered" | "waitlisted" | null;
  stream?: string;
  failRegister?: boolean;
} = {}) {
  let myState: "registered" | "waitlisted" | null = opts.myState ?? null;
  let registered = myState === "registered" ? 1 : 0;
  let waitlisted = myState === "waitlisted" ? 1 : 0;
  const capacity = opts.capacity ?? 2;
  const stream = opts.stream ?? "https://s/x";

  const seatsLeft = () =>
    opts.seatsLeft !== undefined ? opts.seatsLeft : capacity === 0 ? null : Math.max(capacity - registered, 0);

  return vi.fn(async (url: string, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    if (url.includes("/reminders")) {
      return { ok: true, status: 200, json: async () => reminders };
    }
    if (url.includes("/status")) {
      return {
        ok: true,
        status: 200,
        json: async () => ({
          event_id: "e1",
          capacity,
          registered_count: registered,
          waitlisted_count: waitlisted,
          seats_left: seatsLeft(),
          my_state: myState,
          stream_url: stream,
        }),
      };
    }
    if (url.includes("/register") && method === "POST") {
      if (opts.failRegister) {
        return { ok: false, status: 409, json: async () => ({ detail: "Webinar is closed" }) };
      }
      const full = capacity > 0 && registered >= capacity;
      if (full) {
        myState = "waitlisted";
        waitlisted += 1;
      } else {
        myState = "registered";
        registered += 1;
      }
      return { ok: true, status: 201, json: async () => ({ event_id: "e1", status: myState }) };
    }
    if (url.includes("/register") && method === "DELETE") {
      if (myState === "registered") registered -= 1;
      if (myState === "waitlisted") waitlisted -= 1;
      myState = null;
      return { ok: true, status: 200, json: async () => ({ event_id: "e1", status: "cancelled" }) };
    }
    return { ok: false, status: 404, json: async () => ({ detail: "nope" }) };
  }) as unknown as typeof fetch;
}

describe("WebinarPanel", () => {
  it("shows the seat counter and reminders (functional)", async () => {
    const f = makeFetch({ capacity: 2 });
    render(<WebinarPanel eventId="e1" fetchImpl={f} />);
    const seats = await screen.findByTestId("webinar-seats");
    expect(seats).toHaveTextContent("2 of 2 seats left");
    expect(screen.getByTestId("reminder-24h")).toBeInTheDocument();
    expect(screen.getByTestId("reminder-1h")).toBeInTheDocument();
  });

  it("registers and then shows the stream link (functional)", async () => {
    const f = makeFetch({ capacity: 2 });
    render(<WebinarPanel eventId="e1" fetchImpl={f} />);
    const join = await screen.findByTestId("webinar-join");
    await userEvent.click(join);
    await waitFor(() => expect(screen.getByTestId("webinar-stream-link")).toBeInTheDocument());
    expect(screen.getByTestId("webinar-leave")).toBeInTheDocument();
  });

  it("shows a waitlist notice when registering past capacity (functional)", async () => {
    // capacity 1 with the seat already taken by someone else, so the current
    // user's join overflows to the waitlist.
    const f = vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      let myState: string | null = (f as unknown as { _s: string | null })._s ?? null;
      if (url.includes("/reminders")) return { ok: true, status: 200, json: async () => [] };
      if (url.includes("/status"))
        return {
          ok: true,
          status: 200,
          json: async () => ({
            event_id: "e1", capacity: 1, registered_count: 1,
            waitlisted_count: myState === "waitlisted" ? 1 : 0,
            seats_left: 0, my_state: myState, stream_url: "https://s/x",
          }),
        };
      if (url.includes("/register") && method === "POST") {
        (f as unknown as { _s: string | null })._s = "waitlisted";
        return { ok: true, status: 201, json: async () => ({ event_id: "e1", status: "waitlisted" }) };
      }
      return { ok: false, status: 404, json: async () => ({ detail: "nope" }) };
    }) as unknown as typeof fetch;
    render(<WebinarPanel eventId="e1" fetchImpl={f} />);
    const join = await screen.findByTestId("webinar-join");
    expect(join).toHaveTextContent("Join waitlist");
    await userEvent.click(join);
    await waitFor(() => expect(screen.getByTestId("webinar-waitlisted")).toBeInTheDocument());
  });

  it("unlimited capacity shows 'Unlimited seats' (functional)", async () => {
    const f = makeFetch({ capacity: 0 });
    render(<WebinarPanel eventId="e1" fetchImpl={f} />);
    const seats = await screen.findByTestId("webinar-seats");
    expect(seats).toHaveTextContent("Unlimited seats");
  });

  it("lets a registered attendee cancel (functional)", async () => {
    const f = makeFetch({ capacity: 2, myState: "registered" });
    render(<WebinarPanel eventId="e1" fetchImpl={f} />);
    const leave = await screen.findByTestId("webinar-leave");
    await userEvent.click(leave);
    await waitFor(() => expect(screen.getByTestId("webinar-join")).toBeInTheDocument());
  });

  it("surfaces an error when registration fails (negative)", async () => {
    const f = makeFetch({ failRegister: true });
    render(<WebinarPanel eventId="e1" fetchImpl={f} />);
    const join = await screen.findByTestId("webinar-join");
    await userEvent.click(join);
    expect(await screen.findByTestId("webinar-error")).toHaveTextContent("closed");
  });

  it("surfaces an error when cancellation fails (negative)", async () => {
    // registered to start; the DELETE errors
    const f = vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      if (url.includes("/reminders")) return { ok: true, status: 200, json: async () => [] };
      if (url.includes("/status"))
        return {
          ok: true,
          status: 200,
          json: async () => ({
            event_id: "e1", capacity: 2, registered_count: 1, waitlisted_count: 0,
            seats_left: 1, my_state: "registered", stream_url: "https://s/x",
          }),
        };
      if (url.includes("/register") && method === "DELETE")
        return { ok: false, status: 500, json: async () => ({ detail: "server error" }) };
      return { ok: false, status: 404, json: async () => ({ detail: "nope" }) };
    }) as unknown as typeof fetch;
    render(<WebinarPanel eventId="e1" fetchImpl={f} />);
    const leave = await screen.findByTestId("webinar-leave");
    await userEvent.click(leave);
    expect(await screen.findByTestId("webinar-error")).toHaveTextContent("server error");
  });

  it("shows an error and no panel body when loading fails (negative)", async () => {
    const f = vi.fn(async () => ({
      ok: false,
      status: 500,
      json: async () => ({ detail: "boom" }),
    })) as unknown as typeof fetch;
    render(<WebinarPanel eventId="e1" fetchImpl={f} />);
    expect(await screen.findByTestId("webinar-error")).toBeInTheDocument();
    expect(screen.queryByTestId("webinar-seats")).not.toBeInTheDocument();
  });

  it("shows an empty reminders message when none scheduled (negative)", async () => {
    const f = vi.fn(async (url: string) => {
      if (url.includes("/reminders")) return { ok: true, status: 200, json: async () => [] };
      if (url.includes("/status"))
        return {
          ok: true,
          status: 200,
          json: async () => ({
            event_id: "e1", capacity: 0, registered_count: 0, waitlisted_count: 0,
            seats_left: null, my_state: null, stream_url: "",
          }),
        };
      return { ok: false, status: 404, json: async () => ({ detail: "nope" }) };
    }) as unknown as typeof fetch;
    render(<WebinarPanel eventId="e1" fetchImpl={f} />);
    expect(await screen.findByTestId("reminders-empty")).toBeInTheDocument();
  });
});
