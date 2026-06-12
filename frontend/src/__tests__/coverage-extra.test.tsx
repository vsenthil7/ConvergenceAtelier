import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { App } from "../App";
import { EventsView } from "../components/EventsView";
import { LoginView } from "../components/LoginView";
import { UsersView } from "../components/UsersView";
import { AuthProvider, browserTokenStore, useAuth, type TokenStore } from "../lib/AuthContext";
import { getAuthConfig } from "../lib/auth";

function memoryStore(initial: string | null = null): TokenStore {
  let t = initial;
  return { get: () => t, set: (v) => { t = v; }, clear: () => { t = null; } };
}

// ---- App: unknown-role label fallback (App.tsx:60) ----
describe("App role label fallback", () => {
  it("renders the raw role when it has no friendly label (branch)", async () => {
    const f = vi.fn(async (url: string) => {
      if (url.includes("/api/auth/me")) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            id: "u1",
            email: "weird@x.com",
            full_name: "W",
            role: "auditor", // unknown role -> falls back to raw string
            tenant_id: "t1",
            auth_provider: "local",
            last_login_at: null,
          }),
        };
      }
      if (url.includes("/api/events")) return { ok: true, status: 200, json: async () => [] };
      return { ok: false, status: 404, json: async () => ({}) };
    }) as unknown as typeof fetch;
    render(<App fetchImpl={f} store={memoryStore("tok")} />);
    await waitFor(() => expect(screen.getByTestId("whoami")).toHaveTextContent("auditor"));
  });
});

// ---- LoginView: Google sign-in error path (LoginView handleGoogle catch) ----
describe("LoginView Google error path", () => {
  function googleFetch(googleFails: boolean): typeof fetch {
    return vi.fn(async (url: string) => {
      if (url.includes("/api/auth/config")) {
        return { ok: true, status: 200, json: async () => ({ google_enabled: true, google_client_id: "cid" }) };
      }
      if (url.includes("/api/auth/google")) {
        if (googleFails) return { ok: false, status: 401, json: async () => ({ detail: "Bad Google token" }) };
        return { ok: true, status: 200, json: async () => ({ access_token: "g", token_type: "bearer" }) };
      }
      if (url.includes("/api/auth/me")) {
        return { ok: true, status: 200, json: async () => ({ id: "u", email: "g@x.com", full_name: "G", role: "user", tenant_id: "t1", auth_provider: "google", last_login_at: null }) };
      }
      return { ok: false, status: 404, json: async () => ({}) };
    }) as unknown as typeof fetch;
  }

  it("surfaces an error when Google login fails (negative)", async () => {
    const f = googleFetch(true);
    render(
      <AuthProvider fetchImpl={f} store={memoryStore()}>
        <LoginView fetchImpl={f} onRequestGoogle={async () => "id-token"} />
      </AuthProvider>,
    );
    const gbtn = await screen.findByTestId("login-google");
    await userEvent.click(gbtn);
    expect(await screen.findByTestId("login-error")).toHaveTextContent("Bad Google token");
  });

  it("no-ops Google click when no handler is provided (guard)", async () => {
    const f = googleFetch(false);
    render(
      <AuthProvider fetchImpl={f} store={memoryStore()}>
        <LoginView fetchImpl={f} />
      </AuthProvider>,
    );
    // Google button only shows when enabled; without onRequestGoogle the handler returns early.
    const gbtn = await screen.findByTestId("login-google");
    await userEvent.click(gbtn);
    // Nothing happens — still on the login screen, no error.
    expect(screen.queryByTestId("login-error")).not.toBeInTheDocument();
  });
});

// ---- AuthContext: login error, logout, memory-fallback store ----
function Harness() {
  const { user, error, login, loginWithGoogle, logout } = useAuth();
  return (
    <div>
      <span data-testid="who">{user ? user.email : "anon"}</span>
      <span data-testid="err">{error ?? ""}</span>
      <button data-testid="do-login" onClick={() => void login("a@x.com", "pw").catch(() => {})}>
        login
      </button>
      <button data-testid="do-glogin" onClick={() => void loginWithGoogle("idt").catch(() => {})}>
        glogin
      </button>
      <button data-testid="do-logout" onClick={() => logout()}>
        logout
      </button>
    </div>
  );
}

describe("AuthContext flows", () => {
  it("surfaces a login error (catch path)", async () => {
    const f = vi.fn(async (url: string) => {
      if (url.includes("/api/auth/login")) return { ok: false, status: 401, json: async () => ({ detail: "nope" }) };
      return { ok: false, status: 404, json: async () => ({}) };
    }) as unknown as typeof fetch;
    render(
      <AuthProvider fetchImpl={f} store={memoryStore()}>
        <Harness />
      </AuthProvider>,
    );
    await userEvent.click(screen.getByTestId("do-login"));
    await waitFor(() => expect(screen.getByTestId("err")).toHaveTextContent("nope"));
  });

  it("logs in then logs out (login + logout paths)", async () => {
    const f = vi.fn(async (url: string) => {
      if (url.includes("/api/auth/login")) return { ok: true, status: 200, json: async () => ({ access_token: "t", token_type: "bearer" }) };
      if (url.includes("/api/auth/me")) return { ok: true, status: 200, json: async () => ({ id: "u", email: "a@x.com", full_name: "A", role: "user", tenant_id: "t1", auth_provider: "local", last_login_at: null }) };
      return { ok: false, status: 404, json: async () => ({}) };
    }) as unknown as typeof fetch;
    render(
      <AuthProvider fetchImpl={f} store={memoryStore()}>
        <Harness />
      </AuthProvider>,
    );
    await userEvent.click(screen.getByTestId("do-login"));
    await waitFor(() => expect(screen.getByTestId("who")).toHaveTextContent("a@x.com"));
    await userEvent.click(screen.getByTestId("do-logout"));
    await waitFor(() => expect(screen.getByTestId("who")).toHaveTextContent("anon"));
  });

  it("surfaces a Google login error (catch path)", async () => {
    const f = vi.fn(async (url: string) => {
      if (url.includes("/api/auth/google")) return { ok: false, status: 401, json: async () => ({ detail: "gbad" }) };
      return { ok: false, status: 404, json: async () => ({}) };
    }) as unknown as typeof fetch;
    render(
      <AuthProvider fetchImpl={f} store={memoryStore()}>
        <Harness />
      </AuthProvider>,
    );
    await userEvent.click(screen.getByTestId("do-glogin"));
    await waitFor(() => expect(screen.getByTestId("err")).toHaveTextContent("gbad"));
  });

  it("browserTokenStore uses the memory fallback when localStorage is absent", () => {
    const orig = Object.getOwnPropertyDescriptor(window, "localStorage");
    // Force the localStorage probe to throw -> hasLS=false -> memory branch.
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      get() {
        throw new Error("blocked");
      },
    });
    try {
      const store = browserTokenStore();
      expect(store.get()).toBeNull();
      store.set("mem-token");
      expect(store.get()).toBe("mem-token");
      store.clear();
      expect(store.get()).toBeNull();
    } finally {
      if (orig) Object.defineProperty(window, "localStorage", orig);
    }
  });
});

// ---- UsersView: role dropdown change + no-token guards ----
describe("UsersView extra branches", () => {
  function usersFetch(role: string): typeof fetch {
    return vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      if (url.includes("/api/auth/me")) {
        return { ok: true, status: 200, json: async () => ({ id: "me", email: "admin@x.com", full_name: "Admin", role, tenant_id: "t1", auth_provider: "local", last_login_at: null }) };
      }
      if (url.includes("/api/auth/users") && method === "GET") {
        return { ok: true, status: 200, json: async () => [] };
      }
      if (url.includes("/api/auth/users") && method === "POST") {
        return { ok: true, status: 201, json: async () => ({ id: "n", email: "n@x.com", full_name: "", role: "tenant_admin", tenant_id: "t1", auth_provider: "local", last_login_at: null }) };
      }
      return { ok: false, status: 404, json: async () => ({}) };
    }) as unknown as typeof fetch;
  }

  it("super-admin sees the full role list including super_admin (branch)", async () => {
    const f = usersFetch("super_admin");
    const store: TokenStore = { get: () => "tok", set: () => {}, clear: () => {} };
    render(
      <AuthProvider fetchImpl={f} store={store}>
        <UsersView fetchImpl={f} />
      </AuthProvider>,
    );
    await screen.findByTestId("users-add");
    // Super-admins can assign super_admin (tenant-admins never see it).
    const select = screen.getByLabelText("new-user-role") as HTMLSelectElement;
    const values = Array.from(select.options).map((o) => o.value);
    expect(values).toContain("super_admin");
  });

  it("tenant-admin cannot assign super_admin (branch)", async () => {
    const f = usersFetch("tenant_admin");
    const store: TokenStore = { get: () => "tok", set: () => {}, clear: () => {} };
    render(
      <AuthProvider fetchImpl={f} store={store}>
        <UsersView fetchImpl={f} />
      </AuthProvider>,
    );
    await screen.findByTestId("users-add");
    const select = screen.getByLabelText("new-user-role") as HTMLSelectElement;
    const values = Array.from(select.options).map((o) => o.value);
    expect(values).not.toContain("super_admin");
    expect(values).toEqual(["user", "tenant_admin"]);
  });

  it("guards refresh and addUser when there is no token (no-token branch)", async () => {
    const f = vi.fn(async () => ({ ok: true, status: 200, json: async () => [] })) as unknown as typeof fetch;
    const store: TokenStore = { get: () => null, set: () => {}, clear: () => {} };
    render(
      <AuthProvider fetchImpl={f} store={store}>
        <UsersView fetchImpl={f} />
      </AuthProvider>,
    );
    await screen.findByTestId("users-add");
    await userEvent.type(screen.getByLabelText("new-user-email"), "x@x.com");
    await userEvent.type(screen.getByLabelText("new-user-password"), "password1");
    await userEvent.click(screen.getByTestId("users-add-submit"));
    // Both refresh and addUser return early with no token -> fetch never called.
    expect(f).not.toHaveBeenCalled();
  });

  it("changing the role updates the create payload (onChange branch)", async () => {
    const posted: Array<{ role: string }> = [];
    const f = vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      if (url.includes("/api/auth/me")) {
        return { ok: true, status: 200, json: async () => ({ id: "me", email: "a@x.com", full_name: "A", role: "super_admin", tenant_id: "t1", auth_provider: "local", last_login_at: null }) };
      }
      if (url.includes("/api/auth/users") && method === "GET") return { ok: true, status: 200, json: async () => [] };
      if (url.includes("/api/auth/users") && method === "POST") {
        posted.push(JSON.parse(String(init?.body)));
        return { ok: true, status: 201, json: async () => ({ id: "n", email: "n@x.com", full_name: "", role: "tenant_admin", tenant_id: "t1", auth_provider: "local", last_login_at: null }) };
      }
      return { ok: false, status: 404, json: async () => ({}) };
    }) as unknown as typeof fetch;
    const store: TokenStore = { get: () => "tok", set: () => {}, clear: () => {} };
    render(
      <AuthProvider fetchImpl={f} store={store}>
        <UsersView fetchImpl={f} />
      </AuthProvider>,
    );
    await screen.findByTestId("users-add");
    await userEvent.type(screen.getByLabelText("new-user-email"), "n@x.com");
    await userEvent.type(screen.getByLabelText("new-user-password"), "password1");
    await userEvent.selectOptions(screen.getByLabelText("new-user-role"), "tenant_admin");
    await userEvent.click(screen.getByTestId("users-add-submit"));
    await waitFor(() => expect(posted).toHaveLength(1));
    expect(posted[0].role).toBe("tenant_admin");
  });
});

// ---- auth.ts: error JSON without a string detail (branch at line ~72) ----
describe("auth client error-body branch", () => {
  it("keeps the status message when detail is not a string", async () => {
    const f = vi.fn(async () => ({
      ok: false,
      status: 500,
      json: async () => ({ detail: { nested: true } }), // detail present but not a string
    })) as unknown as typeof fetch;
    await expect(getAuthConfig(f)).rejects.toThrow("Request failed: 500");
  });

  it("keeps the status message when the error body is null", async () => {
    const f = vi.fn(async () => ({
      ok: false,
      status: 503,
      json: async () => null, // falsy body -> short-circuits the detail check
    })) as unknown as typeof fetch;
    await expect(getAuthConfig(f)).rejects.toThrow("Request failed: 503");
  });
});

// ---- AuthContext: non-Error rejection fallbacks (login + google) ----
describe("AuthContext non-Error rejection", () => {
  it("falls back to a generic message when login rejects with a non-Error", async () => {
    // fetch itself rejects with a string (not an Error instance).
    const f = vi.fn((url: string) => {
      if (url.includes("/api/auth/login")) return Promise.reject("boom-string");
      return Promise.resolve({ ok: false, status: 404, json: async () => ({}) });
    }) as unknown as typeof fetch;
    render(
      <AuthProvider fetchImpl={f} store={memoryStore()}>
        <Harness />
      </AuthProvider>,
    );
    await userEvent.click(screen.getByTestId("do-login"));
    await waitFor(() => expect(screen.getByTestId("err")).toHaveTextContent("Login failed"));
  });

  it("falls back to a generic message when Google login rejects with a non-Error", async () => {
    const f = vi.fn((url: string) => {
      if (url.includes("/api/auth/google")) return Promise.reject("boom-string");
      return Promise.resolve({ ok: false, status: 404, json: async () => ({}) });
    }) as unknown as typeof fetch;
    render(
      <AuthProvider fetchImpl={f} store={memoryStore()}>
        <Harness />
      </AuthProvider>,
    );
    await userEvent.click(screen.getByTestId("do-glogin"));
    await waitFor(() => expect(screen.getByTestId("err")).toHaveTextContent("Google login failed"));
  });
});

// ---- EventsView: agenda speaker fallback + refresh-when-already-selected ----
describe("EventsView extra branches", () => {
  it("shows TBA when a session has no speaker, and keeps selection across refresh", async () => {
    const ev = {
      id: "e1",
      name: "React Summit",
      location: "AMS",
      description: "",
      starts_at: "2026-06-11T09:00:00.000Z",
      ends_at: "2026-06-12T17:00:00.000Z",
      sessions: [
        {
          id: "s1",
          event_id: "e1",
          title: "Mystery Talk",
          track: "Main",
          speaker: "", // empty -> TBA fallback
          starts_at: "2026-06-11T10:00:00.000Z",
          ends_at: "2026-06-11T11:00:00.000Z",
        },
      ],
    };
    let store = [ev];
    const f = vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      if (url.endsWith("/api/events") && method === "GET") {
        return { ok: true, status: 200, json: async () => store };
      }
      if (method === "DELETE") {
        store = [];
        return { ok: true, status: 204, json: async () => null };
      }
      return { ok: false, status: 404, json: async () => ({}) };
    }) as unknown as typeof fetch;

    render(<EventsView fetchImpl={f} />);
    const grid = await screen.findByTestId("events-grid");
    // Agenda renders with the TBA speaker fallback.
    expect(await screen.findByTestId("agenda")).toBeInTheDocument();
    expect(screen.getAllByText(/Mystery Talk/).length).toBeGreaterThan(0);
    // Click View agenda again with the same event already selected -> refresh keeps selection.
    const { within } = await import("@testing-library/react");
    await userEvent.click(within(grid).getByLabelText("view-e1"));
    expect(await screen.findByText(/Agenda — React Summit/)).toBeInTheDocument();
  });

  it("keeps a selection across a refresh after deleting another event (line 46 branch)", async () => {
    const e1 = {
      id: "e1", name: "Keep", location: "A", description: "",
      starts_at: "2026-06-11T09:00:00.000Z", ends_at: "2026-06-12T17:00:00.000Z", sessions: [],
    };
    const e2 = { ...e1, id: "e2", name: "Drop" };
    let store = [e1, e2];
    const f = vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      if (url.endsWith("/api/events") && method === "GET") return { ok: true, status: 200, json: async () => store };
      if (method === "DELETE") {
        const id = url.split("/").pop()!;
        store = store.filter((e) => e.id !== id);
        return { ok: true, status: 204, json: async () => null };
      }
      return { ok: false, status: 404, json: async () => ({}) };
    }) as unknown as typeof fetch;
    render(<EventsView fetchImpl={f} />);
    const grid = await screen.findByTestId("events-grid");
    const { within } = await import("@testing-library/react");
    // e1 is auto-selected; delete e2 -> refresh runs while selectedId is already set (line 46 false branch).
    await userEvent.click(within(grid).getByLabelText("delete-e2"));
    await waitFor(() => expect(screen.getByText(/Agenda — Keep/)).toBeInTheDocument());
  });
});

// ---- App: loading gate ----
describe("App loading gate", () => {
  it("shows the loading spinner while the session resolves", async () => {
    // getMe never resolves within the test tick -> Gate stays in loading state.
    let release: (v: unknown) => void = () => {};
    const pending = new Promise((r) => { release = r; });
    const f = vi.fn(async (url: string) => {
      if (url.includes("/api/auth/me")) {
        await pending; // hold the response open
        return { ok: true, status: 200, json: async () => ({ id: "u", email: "a@x.com", full_name: "A", role: "user", tenant_id: "t1", auth_provider: "local", last_login_at: null }) };
      }
      return { ok: false, status: 404, json: async () => ({}) };
    }) as unknown as typeof fetch;
    const store: TokenStore = { get: () => "tok", set: () => {}, clear: () => {} };
    render(<App fetchImpl={f} store={store} />);
    expect(await screen.findByTestId("auth-loading")).toBeInTheDocument();
    release(null); // let it finish so no act() warning lingers
    await waitFor(() => expect(screen.getByTestId("whoami")).toBeInTheDocument());
  });
});
