import { describe, it, expect, vi } from "vitest";
import {
  createManagedUser,
  getAuthConfig,
  getMe,
  listUsers,
  login,
  loginGoogle,
  registerPublic,
} from "../lib/auth";

function fetchReturning(status: number, body: unknown, ok = status < 400): typeof fetch {
  return vi.fn(async () => ({ ok, status, json: async () => body })) as unknown as typeof fetch;
}

describe("auth api client", () => {
  it("logs in (functional)", async () => {
    const f = fetchReturning(200, { access_token: "t", token_type: "bearer" });
    const r = await login("a@x.com", "pw", f);
    expect(r.access_token).toBe("t");
  });

  it("google login (functional)", async () => {
    const f = fetchReturning(200, { access_token: "g", token_type: "bearer" });
    const r = await loginGoogle("idtok", f);
    expect(r.access_token).toBe("g");
  });

  it("reads auth config (functional)", async () => {
    const f = fetchReturning(200, { google_enabled: true, google_client_id: "cid" });
    const r = await getAuthConfig(f);
    expect(r.google_enabled).toBe(true);
  });

  it("gets current user with bearer token (functional)", async () => {
    const spy = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({ id: "u1", email: "a@x.com", role: "user" }),
    }));
    await getMe("mytoken", spy as unknown as typeof fetch);
    const init = spy.mock.calls[0][1] as RequestInit;
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer mytoken");
  });

  it("lists users (functional)", async () => {
    const f = fetchReturning(200, [{ id: "u1", email: "a@x.com", role: "user" }]);
    const r = await listUsers("tok", f);
    expect(r).toHaveLength(1);
  });

  it("creates a managed user (functional)", async () => {
    const f = fetchReturning(201, { id: "n", email: "n@x.com", role: "user" });
    const r = await createManagedUser("tok", { email: "n@x.com", password: "password1", role: "user" }, f);
    expect(r.email).toBe("n@x.com");
  });

  it("throws API detail with status on error (negative)", async () => {
    const f = fetchReturning(401, { detail: "Invalid credentials" }, false);
    await expect(login("a@x.com", "bad", f)).rejects.toThrow("Invalid credentials");
  });

  it("falls back to status message on non-JSON error (negative)", async () => {
    const f = vi.fn(async () => ({
      ok: false,
      status: 500,
      json: async () => {
        throw new Error("not json");
      },
    })) as unknown as typeof fetch;
    await expect(getAuthConfig(f)).rejects.toThrow("Request failed: 500");
  });

  it("attaches status code to the thrown error (negative)", async () => {
    const f = fetchReturning(403, { detail: "Forbidden" }, false);
    await expect(listUsers("tok", f)).rejects.toMatchObject({ status: 403 });
  });

  it("posts a public self-registration and returns a token (functional)", async () => {
    const spy = vi.fn(async () => ({
      ok: true,
      status: 201,
      json: async () => ({ access_token: "newtok", token_type: "bearer" }),
    }));
    const out = await registerPublic(
      { email: "new@x.com", full_name: "New", password: "Secret123!", tenant_slug: "react-summit" },
      spy as unknown as typeof fetch,
    );
    expect(out.access_token).toBe("newtok");
    expect(spy.mock.calls[0][0]).toContain("/api/auth/register");
    const init = spy.mock.calls[0][1] as RequestInit;
    expect(JSON.parse(String(init.body)).tenant_slug).toBe("react-summit");
  });

  it("propagates a registration conflict with status (negative)", async () => {
    const f = fetchReturning(409, { detail: "User already exists" }, false);
    await expect(
      registerPublic({ email: "dupe@x.com", password: "Secret123!", tenant_slug: "react-summit" }, f),
    ).rejects.toMatchObject({ status: 409 });
  });
});
