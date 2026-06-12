import { render, screen, waitFor, act } from "@testing-library/react";
import { renderHook } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthProvider, browserTokenStore, useAuth } from "../lib/AuthContext";

function meFetch(): typeof fetch {
  return vi.fn(async (url: string) => {
    if (url.includes("/api/auth/me")) {
      return {
        ok: true,
        status: 200,
        json: async () => ({
          id: "u1",
          email: "a@x.com",
          full_name: "A",
          role: "user",
          tenant_id: "t1",
          auth_provider: "local",
          last_login_at: null,
        }),
      };
    }
    return { ok: false, status: 404, json: async () => ({}) };
  }) as unknown as typeof fetch;
}

function Probe() {
  const { user, loading } = useAuth();
  if (loading) return <span>loading</span>;
  return <span data-testid="probe">{user ? user.email : "anon"}</span>;
}

describe("AuthContext", () => {
  it("throws when useAuth is used outside a provider (negative)", () => {
    // Suppress React's expected error-boundary console noise for this case.
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => renderHook(() => useAuth())).toThrow(/within an AuthProvider/);
    spy.mockRestore();
  });

  it("resolves an anonymous state when no token (functional)", async () => {
    const store = { get: () => null, set: () => {}, clear: () => {} };
    render(
      <AuthProvider fetchImpl={meFetch()} store={store}>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("probe")).toHaveTextContent("anon"));
  });

  it("resolves the user when a token is present (functional)", async () => {
    const store = { get: () => "tok", set: () => {}, clear: () => {} };
    render(
      <AuthProvider fetchImpl={meFetch()} store={store}>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("probe")).toHaveTextContent("a@x.com"));
  });

  it("register() stores the returned token and resolves the new user (functional)", async () => {
    let stored: string | null = null;
    const store = {
      get: () => stored,
      set: (t: string) => {
        stored = t;
      },
      clear: () => {
        stored = null;
      },
    };
    const f = vi.fn(async (url: string) => {
      if (url.includes("/api/auth/register")) {
        return { ok: true, status: 201, json: async () => ({ access_token: "regtok", token_type: "bearer" }) };
      }
      if (url.includes("/api/auth/me")) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            id: "u9", email: "new@x.com", full_name: "New", role: "user",
            tenant_id: "t1", auth_provider: "local", last_login_at: null,
          }),
        };
      }
      return { ok: false, status: 404, json: async () => ({}) };
    }) as unknown as typeof fetch;

    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => (
        <AuthProvider fetchImpl={f} store={store}>
          {children}
        </AuthProvider>
      ),
    });
    await act(async () => {
      await result.current.register({
        email: "new@x.com",
        password: "Secret123!",
        tenant_slug: "react-summit",
      });
    });
    expect(stored).toBe("regtok");
    await waitFor(() => expect(result.current.user?.email).toBe("new@x.com"));
  });

  it("register() surfaces an error on failure (negative)", async () => {
    const store = { get: () => null, set: () => {}, clear: () => {} };
    const f = vi.fn(async () => ({
      ok: false,
      status: 409,
      json: async () => ({ detail: "User already exists" }),
    })) as unknown as typeof fetch;
    const { result } = renderHook(() => useAuth(), {
      wrapper: ({ children }) => (
        <AuthProvider fetchImpl={f} store={store}>
          {children}
        </AuthProvider>
      ),
    });
    await act(async () => {
      await expect(
        result.current.register({ email: "d@x.com", password: "Secret123!", tenant_slug: "react-summit" }),
      ).rejects.toThrow("User already exists");
    });
    await waitFor(() => expect(result.current.error).toBe("User already exists"));
  });
});

describe("browserTokenStore", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("round-trips a token via localStorage (functional)", () => {
    const store = browserTokenStore();
    expect(store.get()).toBeNull();
    store.set("abc");
    expect(store.get()).toBe("abc");
    store.clear();
    expect(store.get()).toBeNull();
  });
});
