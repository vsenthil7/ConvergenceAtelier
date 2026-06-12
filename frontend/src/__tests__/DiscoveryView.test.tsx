import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { DiscoveryView } from "../components/DiscoveryView";

function sessionRow(id: string, title: string, score: number, speaker = "Ada") {
  return {
    score,
    session: {
      id,
      event_id: "e1",
      title,
      track: "Frontend",
      speaker,
      starts_at: "2026-06-11T10:00:00.000Z",
      ends_at: "2026-06-11T11:00:00.000Z",
    },
  };
}

function recommendFetch(rows: unknown[], fails = false): typeof fetch {
  return vi.fn(async (url: string) => {
    if (String(url).includes("/api/events")) {
      return { ok: true, status: 200, json: async () => [] };
    }
    if (fails) return { ok: false, status: 500, json: async () => ({ detail: "boom" }) };
    return { ok: true, status: 200, json: async () => rows };
  }) as unknown as typeof fetch;
}

/** Fetch mock that also serves events + agenda-draft for the AI draft panel. */
function draftFetch(opts: {
  events?: unknown[];
  slots?: unknown[];
  draftFails?: boolean;
}): typeof fetch {
  return vi.fn(async (url: string) => {
    const u = String(url);
    if (u.includes("/agenda-draft")) {
      if (opts.draftFails)
        return { ok: false, status: 500, json: async () => ({ detail: "draft boom" }) };
      return { ok: true, status: 200, json: async () => opts.slots ?? [] };
    }
    if (u.includes("/api/events")) {
      return { ok: true, status: 200, json: async () => opts.events ?? [] };
    }
    if (u.includes("/api/discovery/recommend")) {
      return { ok: true, status: 200, json: async () => [] };
    }
    return { ok: false, status: 404, json: async () => ({ detail: "nf" }) };
  }) as unknown as typeof fetch;
}

function agendaSlot(order: number, title: string, track: string, rel: number, speaker = "Ada") {
  return {
    order,
    relevance: rel,
    track,
    session: {
      id: `s${order}`,
      event_id: "e1",
      title,
      track,
      speaker,
      starts_at: "2026-06-11T10:00:00.000Z",
      ends_at: "2026-06-11T11:00:00.000Z",
    },
  };
}

const EVENT = {
  id: "e1",
  name: "React Summit",
  location: "AMS",
  description: "",
  starts_at: "2026-06-11T09:00:00.000Z",
  ends_at: "2026-06-12T17:00:00.000Z",
  sessions: [],
};

describe("DiscoveryView", () => {
  it("disables Recommend until interests are entered (functional)", async () => {
    render(<DiscoveryView fetchImpl={recommendFetch([])} />);
    const btn = screen.getByTestId("discovery-search");
    expect(btn).toBeDisabled();
    await userEvent.type(screen.getByLabelText("discovery-interests"), "react");
    expect(btn).not.toBeDisabled();
  });

  it("shows ranked results with score badges (functional)", async () => {
    const f = recommendFetch([
      sessionRow("s1", "React hooks deep dive", 0.92),
      sessionRow("s2", "Sourdough baking", 0.10, ""),
    ]);
    render(<DiscoveryView fetchImpl={f} />);
    await userEvent.type(screen.getByLabelText("discovery-interests"), "react");
    await userEvent.click(screen.getByTestId("discovery-search"));
    expect(await screen.findByTestId("discovery-results")).toBeInTheDocument();
    expect(screen.getByText("React hooks deep dive")).toBeInTheDocument();
    // 0.92 -> 92%
    expect(screen.getByLabelText("match-92")).toBeInTheDocument();
    // empty speaker -> TBA fallback
    expect(screen.getByText("TBA")).toBeInTheDocument();
  });

  it("shows an empty state when no sessions come back (functional)", async () => {
    render(<DiscoveryView fetchImpl={recommendFetch([])} />);
    await userEvent.type(screen.getByLabelText("discovery-interests"), "obscure topic");
    await userEvent.click(screen.getByTestId("discovery-search"));
    expect(await screen.findByTestId("discovery-empty")).toBeInTheDocument();
  });

  it("surfaces an error when the API fails (negative)", async () => {
    render(<DiscoveryView fetchImpl={recommendFetch([], true)} />);
    await userEvent.type(screen.getByLabelText("discovery-interests"), "react");
    await userEvent.click(screen.getByTestId("discovery-search"));
    expect(await screen.findByTestId("discovery-error")).toHaveTextContent("boom");
  });

  it("drafts an agenda for the selected event + theme (functional)", async () => {
    const f = draftFetch({
      events: [EVENT],
      slots: [
        agendaSlot(0, "React performance", "Frontend", 0.91),
        agendaSlot(1, "Sourdough", "Lifestyle", 0.05, ""),
      ],
    });
    render(<DiscoveryView fetchImpl={f} />);
    // event dropdown auto-selects the first event once loaded
    await waitFor(() =>
      expect(screen.getByLabelText("agenda-event")).toHaveValue("e1"),
    );
    await userEvent.type(screen.getByLabelText("agenda-theme"), "frontend performance");
    await userEvent.click(screen.getByTestId("agenda-draft-go"));
    expect(await screen.findByTestId("agenda-draft-results")).toBeInTheDocument();
    expect(screen.getByText("React performance")).toBeInTheDocument();
    expect(screen.getByLabelText("relevance-91")).toBeInTheDocument();
    // empty speaker -> TBA fallback in the draft list
    expect(screen.getByText("TBA")).toBeInTheDocument();
  });

  it("shows an empty state when the event has no sessions (functional)", async () => {
    const f = draftFetch({ events: [EVENT], slots: [] });
    render(<DiscoveryView fetchImpl={f} />);
    await waitFor(() => expect(screen.getByLabelText("agenda-event")).toHaveValue("e1"));
    await userEvent.type(screen.getByLabelText("agenda-theme"), "anything");
    await userEvent.click(screen.getByTestId("agenda-draft-go"));
    expect(await screen.findByTestId("agenda-draft-empty")).toBeInTheDocument();
  });

  it("surfaces an error when the agenda draft fails (negative)", async () => {
    const f = draftFetch({ events: [EVENT], draftFails: true });
    render(<DiscoveryView fetchImpl={f} />);
    await waitFor(() => expect(screen.getByLabelText("agenda-event")).toHaveValue("e1"));
    await userEvent.type(screen.getByLabelText("agenda-theme"), "react");
    await userEvent.click(screen.getByTestId("agenda-draft-go"));
    expect(await screen.findByTestId("agenda-draft-error")).toHaveTextContent("draft boom");
  });

  it("keeps Draft disabled until a theme is entered, and shows no-events option (functional + negative)", async () => {
    const f = draftFetch({ events: [] });
    render(<DiscoveryView fetchImpl={f} />);
    // With no events, the placeholder option is present and Draft stays disabled.
    expect(await screen.findByText("No events available")).toBeInTheDocument();
    expect(screen.getByTestId("agenda-draft-go")).toBeDisabled();
  });

  it("recovers gracefully when the events list fails to load (negative)", async () => {
    const f = vi.fn(async (url: string) => {
      if (String(url).includes("/api/events")) {
        return { ok: false, status: 500, json: async () => ({ detail: "events down" }) };
      }
      return { ok: true, status: 200, json: async () => [] };
    }) as unknown as typeof fetch;
    render(<DiscoveryView fetchImpl={f} />);
    // Falls back to the empty-events placeholder; Draft stays disabled, no crash.
    expect(await screen.findByText("No events available")).toBeInTheDocument();
    expect(screen.getByTestId("agenda-draft-go")).toBeDisabled();
  });
});
