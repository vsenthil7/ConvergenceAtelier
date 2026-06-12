import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { App } from "../App";
import type { TokenStore } from "../lib/AuthContext";

/** A controllable in-memory token store for tests (no localStorage). */
function memoryStore(initial: string | null = null): TokenStore {
  let t = initial;
  return {
    get: () => t,
    set: (v: string) => {
      t = v;
    },
    clear: () => {
      t = null;
    },
  };
}

interface Scenario {
  me?: { role: string; email?: string; tenant_id?: string | null };
  events?: unknown[];
  users?: unknown[];
  recommendations?: unknown[];
  googleEnabled?: boolean;
  failMe?: boolean;
}

/** Build a fetch mock covering the auth + events + users endpoints. */
function mockApi(s: Scenario): typeof fetch {
  return vi.fn(async (url: string, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    const ok = (body: unknown, status = 200) => ({
      ok: true,
      status,
      json: async () => body,
    });
    if (url.includes("/api/auth/config")) {
      return ok({ google_enabled: s.googleEnabled ?? false, google_client_id: "cid" });
    }
    if (url.includes("/api/auth/login") && method === "POST") {
      return ok({ access_token: "tok", token_type: "bearer" });
    }
    if (url.includes("/api/auth/google") && method === "POST") {
      return ok({ access_token: "gtok", token_type: "bearer" });
    }
    if (url.includes("/api/auth/me")) {
      if (s.failMe) return { ok: false, status: 401, json: async () => ({ detail: "no" }) };
      return ok({
        id: "u1",
        email: s.me?.email ?? "admin@react-summit.demo",
        full_name: "Admin",
        role: s.me?.role ?? "tenant_admin",
        tenant_id: s.me?.tenant_id ?? "t1",
        auth_provider: "local",
        last_login_at: null,
      });
    }
    if (url.includes("/api/auth/users")) {
      if (method === "POST") return ok({ id: "n", email: "x", full_name: "", role: "user", tenant_id: "t1", auth_provider: "local", last_login_at: null }, 201);
      return ok(s.users ?? []);
    }
    if (url.includes("/api/discovery/recommend")) {
      return ok(s.recommendations ?? []);
    }
    if (url.includes("/api/events")) {
      return ok(s.events ?? []);
    }
    return { ok: false, status: 404, json: async () => ({ detail: "nf" }) };
  }) as unknown as typeof fetch;
}

describe("App auth gate + role-aware shell (S2)", () => {
  it("shows the login screen when no token (functional)", async () => {
    const f = mockApi({});
    render(<App fetchImpl={f} store={memoryStore(null)} />);
    expect(await screen.findByTestId("login-submit")).toBeInTheDocument();
    expect(screen.getByText(/Demo accounts/)).toBeInTheDocument();
  });

  it("logs in and shows the events view + whoami (functional)", async () => {
    const f = mockApi({ me: { role: "tenant_admin" } });
    render(<App fetchImpl={f} store={memoryStore(null)} />);
    await userEvent.type(screen.getByLabelText("login-email"), "admin@react-summit.demo");
    await userEvent.type(screen.getByLabelText("login-password"), "Atelier!2026");
    await userEvent.click(screen.getByTestId("login-submit"));
    await waitFor(() => expect(screen.getByTestId("whoami")).toBeInTheDocument());
    expect(screen.getByTestId("nav-events")).toBeInTheDocument();
  });

  it("restores a session from a stored token (functional)", async () => {
    const f = mockApi({ me: { role: "super_admin", email: "super@atelier.demo" } });
    render(<App fetchImpl={f} store={memoryStore("existing")} />);
    await waitFor(() => expect(screen.getByTestId("whoami")).toBeInTheDocument());
    expect(screen.getByText(/super@atelier.demo/)).toBeInTheDocument();
  });

  it("shows the Users tab only for admins (role-aware)", async () => {
    const f = mockApi({ me: { role: "tenant_admin" } });
    render(<App fetchImpl={f} store={memoryStore("tok")} />);
    await waitFor(() => expect(screen.getByTestId("nav-users")).toBeInTheDocument());
  });

  it("hides the Users tab for attendee role (role-aware negative)", async () => {
    const f = mockApi({ me: { role: "user" } });
    render(<App fetchImpl={f} store={memoryStore("tok")} />);
    await waitFor(() => expect(screen.getByTestId("nav-events")).toBeInTheDocument());
    expect(screen.queryByTestId("nav-users")).not.toBeInTheDocument();
  });

  it("navigates to the Users view for an admin (functional)", async () => {
    const f = mockApi({
      me: { role: "super_admin" },
      users: [
        { id: "u1", email: "a@x.com", full_name: "A", role: "user", tenant_id: "t1", auth_provider: "local", last_login_at: null },
      ],
    });
    render(<App fetchImpl={f} store={memoryStore("tok")} />);
    await userEvent.click(await screen.findByTestId("nav-users"));
    expect(await screen.findByTestId("users-grid")).toBeInTheDocument();
  });

  it("signs out back to the login screen (functional)", async () => {
    const f = mockApi({ me: { role: "tenant_admin" } });
    render(<App fetchImpl={f} store={memoryStore("tok")} />);
    await userEvent.click(await screen.findByTestId("logout"));
    await waitFor(() => expect(screen.getByTestId("login-submit")).toBeInTheDocument());
  });

  it("clears an invalid stored token and shows login (negative)", async () => {
    const f = mockApi({ failMe: true });
    render(<App fetchImpl={f} store={memoryStore("bad")} />);
    await waitFor(() => expect(screen.getByTestId("login-submit")).toBeInTheDocument());
  });

  it("attendee sees events but no New event button (role-aware)", async () => {
    const f = mockApi({
      me: { role: "user" },
      events: [
        {
          id: "e1",
          name: "React Summit",
          location: "AMS",
          description: "",
          starts_at: "2026-06-11T09:00:00.000Z",
          ends_at: "2026-06-12T17:00:00.000Z",
          sessions: [],
        },
      ],
    });
    render(<App fetchImpl={f} store={memoryStore("tok")} />);
    await waitFor(() => expect(screen.getByTestId("events-grid")).toBeInTheDocument());
    expect(screen.queryByTestId("new-event")).not.toBeInTheDocument();
  });

  it("shows the Discover tab to every role and navigates to it (functional)", async () => {
    const f = mockApi({
      me: { role: "user" },
      recommendations: [
        {
          score: 0.88,
          session: {
            id: "s1",
            event_id: "e1",
            title: "React performance",
            track: "Frontend",
            speaker: "Ada",
            starts_at: "2026-06-11T10:00:00.000Z",
            ends_at: "2026-06-11T11:00:00.000Z",
          },
        },
      ],
    });
    render(<App fetchImpl={f} store={memoryStore("tok")} />);
    await userEvent.click(await screen.findByTestId("nav-discover"));
    await userEvent.type(screen.getByLabelText("discovery-interests"), "react");
    await userEvent.click(screen.getByTestId("discovery-search"));
    expect(await screen.findByTestId("discovery-results")).toBeInTheDocument();
    expect(screen.getByText("React performance")).toBeInTheDocument();
  });
});
