import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { LinkedEventsPanel } from "../components/LinkedEventsPanel";

const linkedEvent = {
  id: "e2",
  name: "Online Companion",
  location: "Online",
  event_type: "hybrid" as const,
  starts_at: "2026-07-02T09:00:00+00:00",
  ends_at: "2026-07-02T17:00:00+00:00",
};

const catalogRows = [
  {
    session_id: "s1",
    event_id: "e1",
    event_name: "Flagship",
    title: "In-person Keynote",
    track: "Main",
    speaker: "Jane",
    mode: "in_person",
    stream_url: "",
    recording_url: "",
    starts_at: "2026-07-01T10:00:00+00:00",
  },
  {
    session_id: "s2",
    event_id: "e2",
    event_name: "Online Companion",
    title: "Remote Keynote",
    track: "Main",
    speaker: "Lee",
    mode: "online",
    stream_url: "https://s/x",
    recording_url: "",
    starts_at: "2026-07-02T10:00:00+00:00",
  },
];

/** Mutable mock store so link/unlink reflect in subsequent reads. */
function makeFetch(opts: { startLinked?: boolean; failLink?: boolean; failUnlink?: boolean } = {}) {
  let linked = opts.startLinked ? [linkedEvent] : [];

  return vi.fn(async (url: string, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    if (url.includes("/catalog")) {
      // catalog spans both events only when linked
      const rows = linked.length ? catalogRows : [catalogRows[0]];
      return { ok: true, status: 200, json: async () => rows };
    }
    if (url.includes("/links") && method === "GET") {
      return { ok: true, status: 200, json: async () => linked };
    }
    if (url.includes("/links") && method === "POST") {
      if (opts.failLink) {
        return { ok: false, status: 409, json: async () => ({ detail: "already linked" }) };
      }
      linked = [linkedEvent];
      return { ok: true, status: 201, json: async () => linked };
    }
    if (url.includes("/links/") && method === "DELETE") {
      if (opts.failUnlink) {
        return { ok: false, status: 500, json: async () => ({ detail: "server error" }) };
      }
      linked = [];
      return { ok: true, status: 200, json: async () => linked };
    }
    return { ok: false, status: 404, json: async () => ({ detail: "nope" }) };
  }) as unknown as typeof fetch;
}

const linkable = [
  { id: "e1", name: "Flagship" }, // self — must be filtered out
  { id: "e2", name: "Online Companion" },
  { id: "e3", name: "Another Event" },
];

describe("LinkedEventsPanel", () => {
  it("shows an empty state when there are no links (functional)", async () => {
    const f = makeFetch({ startLinked: false });
    render(<LinkedEventsPanel eventId="e1" linkableEvents={linkable} canManage fetchImpl={f} />);
    expect(await screen.findByTestId("links-empty")).toBeInTheDocument();
  });

  it("renders the linked list with an unlink control for admins (functional)", async () => {
    const f = makeFetch({ startLinked: true });
    render(<LinkedEventsPanel eventId="e1" linkableEvents={linkable} canManage fetchImpl={f} />);
    const list = await screen.findByTestId("linked-list");
    expect(within(list).getByText("Online Companion")).toBeInTheDocument();
    expect(screen.getByTestId("unlink-e2")).toBeInTheDocument();
  });

  it("links an event via the select + button (functional)", async () => {
    const f = makeFetch({ startLinked: false });
    render(<LinkedEventsPanel eventId="e1" linkableEvents={linkable} canManage fetchImpl={f} />);
    await screen.findByTestId("links-empty");
    await userEvent.selectOptions(screen.getByLabelText("link-target"), "e2");
    await userEvent.click(screen.getByTestId("link-button"));
    await waitFor(() => expect(screen.getByTestId("linked-list")).toBeInTheDocument());
    expect(screen.getByTestId("unlink-e2")).toBeInTheDocument();
  });

  it("unlinks an event (functional)", async () => {
    const f = makeFetch({ startLinked: true });
    render(<LinkedEventsPanel eventId="e1" linkableEvents={linkable} canManage fetchImpl={f} />);
    const unlink = await screen.findByTestId("unlink-e2");
    await userEvent.click(unlink);
    await waitFor(() => expect(screen.getByTestId("links-empty")).toBeInTheDocument());
  });

  it("renders the combined 'Across this series' catalog (functional)", async () => {
    const f = makeFetch({ startLinked: true });
    render(<LinkedEventsPanel eventId="e1" linkableEvents={linkable} canManage fetchImpl={f} />);
    const catalog = await screen.findByTestId("series-catalog");
    expect(within(catalog).getByText(/Across this series \(2\)/)).toBeInTheDocument();
    expect(screen.getByTestId("series-s1")).toBeInTheDocument();
    expect(screen.getByTestId("series-s2")).toBeInTheDocument();
  });

  it("filters self + already-linked from the link picker (functional)", async () => {
    const f = makeFetch({ startLinked: true });
    render(<LinkedEventsPanel eventId="e1" linkableEvents={linkable} canManage fetchImpl={f} />);
    await screen.findByTestId("linked-list");
    const select = screen.getByLabelText("link-target") as HTMLSelectElement;
    const values = Array.from(select.options).map((o) => o.value);
    // e1 is self, e2 is already linked → only e3 remains (plus the empty default)
    expect(values).toEqual(["", "e3"]);
  });

  it("hides link/unlink controls when canManage is false (role-aware negative)", async () => {
    const f = makeFetch({ startLinked: true });
    render(<LinkedEventsPanel eventId="e1" linkableEvents={linkable} canManage={false} fetchImpl={f} />);
    await screen.findByTestId("linked-list");
    expect(screen.queryByTestId("unlink-e2")).not.toBeInTheDocument();
    expect(screen.queryByTestId("linked-add")).not.toBeInTheDocument();
  });

  it("surfaces an error when linking fails (negative)", async () => {
    const f = makeFetch({ startLinked: false, failLink: true });
    render(<LinkedEventsPanel eventId="e1" linkableEvents={linkable} canManage fetchImpl={f} />);
    await screen.findByTestId("links-empty");
    await userEvent.selectOptions(screen.getByLabelText("link-target"), "e2");
    await userEvent.click(screen.getByTestId("link-button"));
    expect(await screen.findByTestId("linked-error")).toHaveTextContent("already linked");
  });

  it("surfaces an error when unlinking fails (negative)", async () => {
    const f = makeFetch({ startLinked: true, failUnlink: true });
    render(<LinkedEventsPanel eventId="e1" linkableEvents={linkable} canManage fetchImpl={f} />);
    const unlink = await screen.findByTestId("unlink-e2");
    await userEvent.click(unlink);
    expect(await screen.findByTestId("linked-error")).toHaveTextContent("server error");
  });

  it("shows an error when loading fails (negative)", async () => {
    const f = vi.fn(async () => ({
      ok: false,
      status: 500,
      json: async () => ({ detail: "boom" }),
    })) as unknown as typeof fetch;
    render(<LinkedEventsPanel eventId="e1" linkableEvents={linkable} canManage fetchImpl={f} />);
    expect(await screen.findByTestId("linked-error")).toBeInTheDocument();
  });

  it("shows a catalog-empty message when the series has no sessions (negative)", async () => {
    const f = vi.fn(async (url: string) => {
      if (url.includes("/catalog")) return { ok: true, status: 200, json: async () => [] };
      if (url.includes("/links")) return { ok: true, status: 200, json: async () => [] };
      return { ok: false, status: 404, json: async () => ({ detail: "nope" }) };
    }) as unknown as typeof fetch;
    render(<LinkedEventsPanel eventId="e1" linkableEvents={[]} canManage fetchImpl={f} />);
    expect(await screen.findByTestId("catalog-empty")).toBeInTheDocument();
  });

  it("uses a fallback message when a load rejects with a non-Error (negative)", async () => {
    // reject with a plain string so the `instanceof Error` ternary takes its else branch
    const f = vi.fn(async () => {
      throw "plain string failure";
    }) as unknown as typeof fetch;
    render(<LinkedEventsPanel eventId="e1" linkableEvents={linkable} canManage fetchImpl={f} />);
    expect(await screen.findByTestId("linked-error")).toHaveTextContent(
      "Failed to load linked events",
    );
  });

  it("uses a fallback message when linking rejects with a non-Error (negative)", async () => {
    let calls = 0;
    const f = vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      if (url.includes("/links") && method === "POST") throw "boom";
      // initial loads succeed (empty), so the empty state + picker render
      if (url.includes("/catalog")) return { ok: true, status: 200, json: async () => [] };
      if (url.includes("/links")) {
        calls += 1;
        return { ok: true, status: 200, json: async () => [] };
      }
      return { ok: false, status: 404, json: async () => ({ detail: "nope" }) };
    }) as unknown as typeof fetch;
    render(<LinkedEventsPanel eventId="e1" linkableEvents={linkable} canManage fetchImpl={f} />);
    await screen.findByTestId("links-empty");
    await userEvent.selectOptions(screen.getByLabelText("link-target"), "e2");
    await userEvent.click(screen.getByTestId("link-button"));
    expect(await screen.findByTestId("linked-error")).toHaveTextContent("Could not link event");
    expect(calls).toBeGreaterThan(0);
  });

  it("uses a fallback message when unlinking rejects with a non-Error (negative)", async () => {
    const f = vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      if (url.includes("/links/") && method === "DELETE") throw "boom";
      if (url.includes("/catalog")) return { ok: true, status: 200, json: async () => [] };
      if (url.includes("/links")) return { ok: true, status: 200, json: async () => [linkedEvent] };
      return { ok: false, status: 404, json: async () => ({ detail: "nope" }) };
    }) as unknown as typeof fetch;
    render(<LinkedEventsPanel eventId="e1" linkableEvents={linkable} canManage fetchImpl={f} />);
    const unlink = await screen.findByTestId("unlink-e2");
    await userEvent.click(unlink);
    expect(await screen.findByTestId("linked-error")).toHaveTextContent("Could not unlink event");
  });
});
