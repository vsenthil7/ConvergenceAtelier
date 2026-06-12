import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { LoginView } from "../components/LoginView";
import { AuthProvider, type TokenStore } from "../lib/AuthContext";

function memoryStore(): TokenStore {
  let t: string | null = null;
  return { get: () => t, set: (v) => { t = v; }, clear: () => { t = null; } };
}

function mockFetch(opts: { googleEnabled?: boolean; loginFails?: boolean }): typeof fetch {
  return vi.fn(async (url: string, init?: RequestInit) => {
    if (url.includes("/api/auth/config")) {
      return { ok: true, status: 200, json: async () => ({ google_enabled: !!opts.googleEnabled, google_client_id: "cid" }) };
    }
    if (url.includes("/api/auth/login")) {
      if (opts.loginFails) return { ok: false, status: 401, json: async () => ({ detail: "Invalid credentials" }) };
      return { ok: true, status: 200, json: async () => ({ access_token: "t", token_type: "bearer" }) };
    }
    if (url.includes("/api/auth/google")) {
      return { ok: true, status: 200, json: async () => ({ access_token: "g", token_type: "bearer" }) };
    }
    if (url.includes("/api/auth/me")) {
      return { ok: true, status: 200, json: async () => ({ id: "u1", email: "a@x.com", full_name: "A", role: "user", tenant_id: "t1", auth_provider: "local", last_login_at: null }) };
    }
    return { ok: false, status: 404, json: async () => ({}) };
  }) as unknown as typeof fetch;
}

function renderLogin(f: typeof fetch, extra?: { onRequestGoogle?: () => Promise<string> }) {
  return render(
    <AuthProvider fetchImpl={f} store={memoryStore()}>
      <LoginView fetchImpl={f} onRequestGoogle={extra?.onRequestGoogle} />
    </AuthProvider>,
  );
}

describe("LoginView", () => {
  it("disables submit until email + password entered (functional)", async () => {
    renderLogin(mockFetch({}));
    const submit = screen.getByTestId("login-submit");
    expect(submit).toBeDisabled();
    await userEvent.type(screen.getByLabelText("login-email"), "a@x.com");
    await userEvent.type(screen.getByLabelText("login-password"), "pw");
    expect(submit).not.toBeDisabled();
  });

  it("shows an error on failed login (negative)", async () => {
    renderLogin(mockFetch({ loginFails: true }));
    await userEvent.type(screen.getByLabelText("login-email"), "a@x.com");
    await userEvent.type(screen.getByLabelText("login-password"), "bad");
    await userEvent.click(screen.getByTestId("login-submit"));
    expect(await screen.findByTestId("login-error")).toHaveTextContent("Invalid credentials");
  });

  it("hides the Google button when SSO disabled (role-aware negative)", async () => {
    renderLogin(mockFetch({ googleEnabled: false }));
    await waitFor(() => expect(screen.getByTestId("login-submit")).toBeInTheDocument());
    expect(screen.queryByTestId("login-google")).not.toBeInTheDocument();
  });

  it("shows the Google button and signs in via SSO (functional)", async () => {
    const onRequestGoogle = vi.fn(async () => "id-token");
    renderLogin(mockFetch({ googleEnabled: true }), { onRequestGoogle });
    const gbtn = await screen.findByTestId("login-google");
    await userEvent.click(gbtn);
    await waitFor(() => expect(onRequestGoogle).toHaveBeenCalled());
  });

  it("falls back to no Google when config fetch fails (negative)", async () => {
    const f = vi.fn(async (url: string) => {
      if (url.includes("/api/auth/config")) return { ok: false, status: 500, json: async () => ({}) };
      return { ok: true, status: 200, json: async () => ({}) };
    }) as unknown as typeof fetch;
    renderLogin(f);
    await waitFor(() => expect(screen.getByTestId("login-submit")).toBeInTheDocument());
    expect(screen.queryByTestId("login-google")).not.toBeInTheDocument();
  });
});
