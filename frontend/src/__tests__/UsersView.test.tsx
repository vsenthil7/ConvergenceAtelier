import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { UsersView } from "../components/UsersView";
import { AuthProvider, type TokenStore } from "../lib/AuthContext";

function fixedStore(token: string): TokenStore {
  return { get: () => token, set: () => {}, clear: () => {} };
}

interface Opts {
  role?: string;
  users?: unknown[];
  listFails?: boolean;
  createFails?: boolean;
}

function mockFetch(opts: Opts) {
  let store = [...(opts.users ?? [])];
  const impl = vi.fn(async (url: string, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    if (url.includes("/api/auth/me")) {
      return {
        ok: true,
        status: 200,
        json: async () => ({
          id: "me",
          email: "admin@x.com",
          full_name: "Admin",
          role: opts.role ?? "tenant_admin",
          tenant_id: "t1",
          auth_provider: "local",
          last_login_at: null,
        }),
      };
    }
    if (url.includes("/api/auth/users") && method === "GET") {
      if (opts.listFails) return { ok: false, status: 403, json: async () => ({ detail: "Forbidden" }) };
      return { ok: true, status: 200, json: async () => store };
    }
    if (url.includes("/api/auth/users") && method === "POST") {
      if (opts.createFails) return { ok: false, status: 409, json: async () => ({ detail: "User already exists" }) };
      const created = { ...JSON.parse(String(init?.body)), id: "n", auth_provider: "local", last_login_at: null };
      store = [...store, created];
      return { ok: true, status: 201, json: async () => created };
    }
    return { ok: false, status: 404, json: async () => ({}) };
  }) as unknown as typeof fetch;
  return impl;
}

function renderUsers(f: typeof fetch) {
  return render(
    <AuthProvider fetchImpl={f} store={fixedStore("tok")}>
      <UsersView fetchImpl={f} />
    </AuthProvider>,
  );
}

describe("UsersView", () => {
  it("lists users in a grid (functional)", async () => {
    const f = mockFetch({
      users: [
        { id: "u1", email: "a@x.com", full_name: "A", role: "user", tenant_id: "t1", auth_provider: "local", last_login_at: null },
      ],
    });
    renderUsers(f);
    expect(await screen.findByTestId("users-grid")).toBeInTheDocument();
    expect(screen.getByText("a@x.com")).toBeInTheDocument();
  });

  it("shows an error when listing fails (negative)", async () => {
    const f = mockFetch({ listFails: true });
    renderUsers(f);
    expect(await screen.findByTestId("users-error")).toHaveTextContent("Forbidden");
  });

  it("creates a user and refreshes the grid (functional)", async () => {
    const f = mockFetch({ users: [] });
    renderUsers(f);
    await screen.findByTestId("users-add");
    await userEvent.type(screen.getByLabelText("new-user-email"), "new@x.com");
    await userEvent.type(screen.getByLabelText("new-user-password"), "password1");
    await userEvent.click(screen.getByTestId("users-add-submit"));
    await waitFor(() => expect(screen.getByText("new@x.com")).toBeInTheDocument());
  });

  it("disables submit until password is long enough (negative)", async () => {
    const f = mockFetch({ users: [] });
    renderUsers(f);
    await screen.findByTestId("users-add");
    await userEvent.type(screen.getByLabelText("new-user-email"), "new@x.com");
    await userEvent.type(screen.getByLabelText("new-user-password"), "short");
    expect(screen.getByTestId("users-add-submit")).toBeDisabled();
  });

  it("surfaces a create conflict error (negative)", async () => {
    const f = mockFetch({ users: [], createFails: true });
    renderUsers(f);
    await screen.findByTestId("users-add");
    await userEvent.type(screen.getByLabelText("new-user-email"), "dup@x.com");
    await userEvent.type(screen.getByLabelText("new-user-password"), "password1");
    await userEvent.click(screen.getByTestId("users-add-submit"));
    expect(await screen.findByTestId("users-form-error")).toHaveTextContent("already exists");
  });
});
