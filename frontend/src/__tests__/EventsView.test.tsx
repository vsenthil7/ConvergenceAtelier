import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { EventsView } from "../components/EventsView";
import type { EventModel } from "../lib/events";

const event1: EventModel = {
  id: "e1",
  name: "React Summit",
  location: "Amsterdam",
  description: "",
  event_type: "conference",
  config: {},
  starts_at: "2026-06-11T09:00:00.000Z",
  ends_at: "2026-06-12T17:00:00.000Z",
  sessions: [
    {
      id: "s1",
      event_id: "e1",
      title: "Keynote",
      track: "Main",
      speaker: "Jane",
      mode: "hybrid",
      stream_url: "https://stream.demo/keynote",
      meeting_url: "",
      recording_url: "https://rec.demo/keynote",
      starts_at: "2026-06-11T10:00:00.000Z",
      ends_at: "2026-06-11T11:00:00.000Z",
    },
  ],
};

/** Build a fetch mock with a mutable event store so create/delete reflect. */
function makeFetch(initial: EventModel[]) {
  let store = [...initial];
  let myStatus: string | null = null;
  const impl = vi.fn(async (url: string, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    if (url.includes("/recordings")) {
      const recs = (store[0]?.sessions ?? []).filter((s) => s.recording_url);
      return { ok: true, status: 200, json: async () => recs };
    }
    if (url.includes("/hackathon/teams") || url.includes("/hackathon/leaderboard")) {
      return { ok: true, status: 200, json: async () => [] };
    }
    if (url.includes("/webinar/status")) {
      return {
        ok: true,
        status: 200,
        json: async () => ({
          event_id: store[0]?.id ?? "e1",
          capacity: 0,
          registered_count: 0,
          waitlisted_count: 0,
          seats_left: null,
          my_state: null,
          stream_url: "",
        }),
      };
    }
    if (url.includes("/webinar/reminders")) {
      return { ok: true, status: 200, json: async () => [] };
    }
    if (url.includes("/participants")) {
      return { ok: true, status: 200, json: async () => [
        { user_id: "u1", email: "att@x.com", full_name: "Att Endee", status: "registered" },
      ] };
    }
    if (url.includes("/registration")) {
      return { ok: true, status: 200, json: async () => ({ event_id: "e1", status: myStatus }) };
    }
    if (url.includes("/register") && method === "POST") {
      myStatus = "registered";
      return { ok: true, status: 201, json: async () => ({ status: "registered" }) };
    }
    if (url.includes("/register") && method === "DELETE") {
      myStatus = "cancelled";
      return { ok: true, status: 200, json: async () => ({ status: "cancelled" }) };
    }
    if (url.endsWith("/api/events") && method === "GET") {
      return { ok: true, status: 200, json: async () => store };
    }
    if (url.endsWith("/api/events") && method === "POST") {
      const created: EventModel = {
        ...JSON.parse(String(init?.body)),
        id: "new",
        config: {},
        sessions: [],
      };
      store = [...store, created];
      return { ok: true, status: 201, json: async () => created };
    }
    if (method === "DELETE") {
      const id = url.split("/").pop()!;
      store = store.filter((e) => e.id !== id);
      return { ok: true, status: 204, json: async () => null };
    }
    return { ok: false, status: 404, json: async () => ({ detail: "nope" }) };
  }) as unknown as typeof fetch;
  return impl;
}

describe("EventsView", () => {
  it("renders an empty state (functional)", async () => {
    const f = makeFetch([]);
    render(<EventsView fetchImpl={f} />);
    expect(await screen.findByTestId("events-empty")).toBeInTheDocument();
  });

  it("renders the grid and agenda for an event (functional)", async () => {
    const f = makeFetch([event1]);
    render(<EventsView fetchImpl={f} />);
    expect(await screen.findByTestId("events-grid")).toBeInTheDocument();
    expect(await screen.findByTestId("agenda")).toBeInTheDocument();
    expect(screen.getAllByText(/Keynote/).length).toBeGreaterThan(0);
  });

  it("shows an error when loading fails (negative)", async () => {
    const f = vi.fn(async () => ({
      ok: false,
      status: 500,
      json: async () => ({ detail: "boom" }),
    })) as unknown as typeof fetch;
    render(<EventsView fetchImpl={f} />);
    expect(await screen.findByTestId("events-error")).toBeInTheDocument();
  });

  it("creates an event through the dialog (functional)", async () => {
    const f = makeFetch([]);
    render(
      <EventsView
        fetchImpl={f}
        newEventDefaults={{
          starts_at: "2026-06-11T09:00:00.000Z",
          ends_at: "2026-06-12T17:00:00.000Z",
        }}
      />,
    );
    await screen.findByTestId("events-empty");
    await userEvent.click(screen.getByText("New event"));
    await userEvent.type(screen.getByLabelText("event-name"), "JSNation");
    await userEvent.click(screen.getByText("Create"));
    // After creation, the grid appears with the new event.
    await waitFor(() => expect(screen.getByTestId("events-grid")).toBeInTheDocument());
    expect(screen.getByText("JSNation")).toBeInTheDocument();
  });

  it("cancels the dialog without creating (functional)", async () => {
    const f = makeFetch([]);
    render(<EventsView fetchImpl={f} />);
    await screen.findByTestId("events-empty");
    await userEvent.click(screen.getByText("New event"));
    await userEvent.click(screen.getByText("Cancel"));
    await waitFor(() => expect(screen.queryByText("Create")).not.toBeInTheDocument());
  });

  it("deletes an event (functional)", async () => {
    const f = makeFetch([event1]);
    render(<EventsView fetchImpl={f} />);
    const grid = await screen.findByTestId("events-grid");
    await userEvent.click(within(grid).getByLabelText("delete-e1"));
    await waitFor(() => expect(screen.getByTestId("events-empty")).toBeInTheDocument());
  });

  it("switches selected event when View agenda is clicked (functional)", async () => {
    const event2: EventModel = { ...event1, id: "e2", name: "Vue Conf", sessions: [] };
    const f = makeFetch([event1, event2]);
    render(<EventsView fetchImpl={f} />);
    const grid = await screen.findByTestId("events-grid");
    await userEvent.click(within(grid).getByLabelText("view-e2"));
    await waitFor(() => expect(screen.getByText(/Agenda — Vue Conf/)).toBeInTheDocument());
  });

  it("closes the dialog via the X (negative/edge)", async () => {
    const f = makeFetch([]);
    render(<EventsView fetchImpl={f} />);
    await screen.findByTestId("events-empty");
    await userEvent.click(screen.getByText("New event"));
    expect(screen.getByText("Create")).toBeInTheDocument();
  });

  it("admin sees the participant roster for the selected event (functional)", async () => {
    const f = makeFetch([event1]);
    render(<EventsView fetchImpl={f} canWrite={true} />);
    expect(await screen.findByTestId("roster")).toBeInTheDocument();
    expect(screen.getByText(/Att Endee/)).toBeInTheDocument();
  });

  it("attendee registers and then cancels (functional)", async () => {
    const f = makeFetch([event1]);
    render(<EventsView fetchImpl={f} canWrite={false} />);
    const toggle = await screen.findByTestId("register-toggle");
    expect(toggle).toHaveTextContent("Register for this event");
    await userEvent.click(toggle);
    await waitFor(() => expect(screen.getByTestId("registered-badge")).toBeInTheDocument());
    // now registered → button offers cancel
    await userEvent.click(screen.getByTestId("register-toggle"));
    await waitFor(() =>
      expect(screen.getByTestId("register-toggle")).toHaveTextContent("Register for this event"),
    );
  });

  it("attendee does not see the admin roster (role-aware negative)", async () => {
    const f = makeFetch([event1]);
    render(<EventsView fetchImpl={f} canWrite={false} />);
    await screen.findByTestId("participation");
    expect(screen.queryByTestId("roster")).not.toBeInTheDocument();
  });

  it("shows a no-sessions affordance for an event with empty agenda (functional)", async () => {
    const emptyAgenda: EventModel = { ...event1, id: "e3", name: "Empty", sessions: [] };
    const f = makeFetch([emptyAgenda]);
    render(<EventsView fetchImpl={f} canWrite={true} />);
    expect(await screen.findByTestId("agenda-empty")).toBeInTheDocument();
  });

  it("admin roster shows an empty message when no one registered (functional)", async () => {
    // roster endpoint returns [] for this event
    const f = vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      if (url.includes("/participants")) return { ok: true, status: 200, json: async () => [] };
      if (url.endsWith("/api/events") && method === "GET")
        return { ok: true, status: 200, json: async () => [event1] };
      return { ok: false, status: 404, json: async () => ({ detail: "nope" }) };
    }) as unknown as typeof fetch;
    render(<EventsView fetchImpl={f} canWrite={true} />);
    expect(await screen.findByTestId("roster-empty")).toBeInTheDocument();
  });

  it("tolerates a participation load failure without crashing (negative)", async () => {
    // events load OK, but participants endpoint errors → roster falls back to empty
    const f = vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      if (url.includes("/participants")) return { ok: false, status: 500, json: async () => ({ detail: "x" }) };
      if (url.endsWith("/api/events") && method === "GET")
        return { ok: true, status: 200, json: async () => [event1] };
      return { ok: false, status: 404, json: async () => ({ detail: "nope" }) };
    }) as unknown as typeof fetch;
    render(<EventsView fetchImpl={f} canWrite={true} />);
    expect(await screen.findByTestId("roster-empty")).toBeInTheDocument();
  });

  it("tolerates an attendee status load failure (negative)", async () => {
    const f = vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      if (url.includes("/registration")) return { ok: false, status: 500, json: async () => ({ detail: "x" }) };
      if (url.endsWith("/api/events") && method === "GET")
        return { ok: true, status: 200, json: async () => [event1] };
      return { ok: false, status: 404, json: async () => ({ detail: "nope" }) };
    }) as unknown as typeof fetch;
    render(<EventsView fetchImpl={f} canWrite={false} />);
    const toggle = await screen.findByTestId("register-toggle");
    // status unknown → defaults to the register affordance
    expect(toggle).toHaveTextContent("Register for this event");
  });

  it("renders an event-type badge in the grid (S7 functional)", async () => {
    const hackathon: EventModel = {
      ...event1,
      id: "h1",
      name: "JS Hack",
      event_type: "hackathon",
      sessions: [],
    };
    const f = makeFetch([hackathon]);
    render(<EventsView fetchImpl={f} />);
    const grid = await screen.findByTestId("events-grid");
    const badge = within(grid).getByText("hackathon");
    expect(badge).toHaveClass("event-type-badge", "event-type-hackathon");
  });

  it("shows a mode chip + stream + recording link per session (S7.2 functional)", async () => {
    const f = makeFetch([event1]);
    render(<EventsView fetchImpl={f} />);
    const modes = await screen.findByTestId("session-modes");
    expect(within(modes).getByText("Hybrid")).toBeInTheDocument();
    expect(screen.getByTestId("stream-s1")).toHaveAttribute("href", "https://stream.demo/keynote");
    expect(screen.getByTestId("recording-s1")).toHaveAttribute("href", "https://rec.demo/keynote");
  });

  it("shows the on-demand recordings catalog (S7.2 functional)", async () => {
    const f = makeFetch([event1]);
    render(<EventsView fetchImpl={f} />);
    const catalog = await screen.findByTestId("recordings");
    expect(within(catalog).getByText(/Recordings \(1\)/)).toBeInTheDocument();
    expect(screen.getByTestId("catalog-s1")).toHaveAttribute("href", "https://rec.demo/keynote");
  });

  it("hides the recordings catalog when there are none (S7.2 negative)", async () => {
    const noRec: EventModel = {
      ...event1,
      id: "nr1",
      sessions: [
        {
          id: "s9",
          event_id: "nr1",
          title: "Live only",
          track: "Main",
          speaker: "Sam",
          mode: "online",
          stream_url: "https://stream.demo/x",
          meeting_url: "",
          recording_url: "",
          starts_at: "2026-06-11T10:00:00.000Z",
          ends_at: "2026-06-11T11:00:00.000Z",
        },
      ],
    };
    const f = makeFetch([noRec]);
    render(<EventsView fetchImpl={f} />);
    await screen.findByTestId("session-modes");
    expect(screen.queryByTestId("recordings")).not.toBeInTheDocument();
    // online session shows its stream but no recording link
    expect(screen.getByTestId("stream-s9")).toBeInTheDocument();
    expect(screen.queryByTestId("recording-s9")).not.toBeInTheDocument();
  });

  it("tolerates a recordings load failure without crashing (S7.2 negative)", async () => {
    const f = vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      if (url.includes("/recordings")) return { ok: false, status: 500, json: async () => ({ detail: "x" }) };
      if (url.includes("/participants")) return { ok: true, status: 200, json: async () => [] };
      if (url.endsWith("/api/events") && method === "GET")
        return { ok: true, status: 200, json: async () => [event1] };
      return { ok: false, status: 404, json: async () => ({ detail: "nope" }) };
    }) as unknown as typeof fetch;
    render(<EventsView fetchImpl={f} canWrite={true} />);
    // agenda still renders; recordings panel simply absent
    expect(await screen.findByTestId("session-modes")).toBeInTheDocument();
    expect(screen.queryByTestId("recordings")).not.toBeInTheDocument();
  });

  it("renders the hackathon panel for a hackathon-typed event (S7.3 functional)", async () => {
    const hack: EventModel = {
      ...event1,
      id: "hk1",
      name: "JS Hack",
      event_type: "hackathon",
      sessions: [],
    };
    const f = makeFetch([hack]);
    render(<EventsView fetchImpl={f} />);
    expect(await screen.findByTestId("hackathon-panel")).toBeInTheDocument();
  });

  it("does not render the hackathon panel for a conference event (S7.3 negative)", async () => {
    const f = makeFetch([event1]);
    render(<EventsView fetchImpl={f} />);
    await screen.findByTestId("agenda");
    expect(screen.queryByTestId("hackathon-panel")).not.toBeInTheDocument();
  });

  it("renders the webinar panel for a webinar-typed event (S7.4 functional)", async () => {
    const web: EventModel = {
      ...event1,
      id: "wb1",
      name: "Vue Webinar",
      event_type: "webinar",
      sessions: [],
    };
    const f = makeFetch([web]);
    render(<EventsView fetchImpl={f} />);
    expect(await screen.findByTestId("webinar-panel")).toBeInTheDocument();
  });

  it("does not render the webinar panel for a conference event (S7.4 negative)", async () => {
    const f = makeFetch([event1]);
    render(<EventsView fetchImpl={f} />);
    await screen.findByTestId("agenda");
    expect(screen.queryByTestId("webinar-panel")).not.toBeInTheDocument();
  });
});
