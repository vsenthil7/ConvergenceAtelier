import { render, screen, waitFor } from "@testing-library/react";
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
