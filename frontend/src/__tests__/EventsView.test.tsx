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
  starts_at: "2026-06-11T09:00:00.000Z",
  ends_at: "2026-06-12T17:00:00.000Z",
  sessions: [
    {
      id: "s1",
      event_id: "e1",
      title: "Keynote",
      track: "Main",
      speaker: "Jane",
      starts_at: "2026-06-11T10:00:00.000Z",
      ends_at: "2026-06-11T11:00:00.000Z",
    },
  ],
};

/** Build a fetch mock with a mutable event store so create/delete reflect. */
function makeFetch(initial: EventModel[]) {
  let store = [...initial];
  const impl = vi.fn(async (url: string, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    if (url.endsWith("/api/events") && method === "GET") {
      return { ok: true, status: 200, json: async () => store };
    }
    if (url.endsWith("/api/events") && method === "POST") {
      const created: EventModel = {
        ...JSON.parse(String(init?.body)),
        id: "new",
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
    expect(screen.getByText(/Keynote/)).toBeInTheDocument();
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
});
