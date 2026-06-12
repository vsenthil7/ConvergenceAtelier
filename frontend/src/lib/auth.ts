// Typed client for the auth + identity API (S2).
// Pure functions with an injectable fetch so every path is unit-testable.

export type Role = "super_admin" | "tenant_admin" | "user";

export interface CurrentUser {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  tenant_id: string | null;
  auth_provider: string;
  last_login_at: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface AuthConfig {
  google_enabled: boolean;
  google_client_id: string;
}

export interface ManagedUser {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  tenant_id: string | null;
  auth_provider: string;
  last_login_at: string | null;
}

export interface NewUserInput {
  email: string;
  full_name?: string;
  password: string;
  role: Role;
  tenant_id?: string | null;
}

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

async function request<T>(
  path: string,
  init: RequestInit,
  token: string | null,
  fetchImpl: typeof fetch,
  expectBody = true,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const resp = await fetchImpl(`${API_BASE}${path}`, { ...init, headers });
  if (!resp.ok) {
    let detail = `Request failed: ${resp.status}`;
    try {
      const body = await resp.json();
      if (body && typeof body.detail === "string") detail = body.detail;
    } catch {
      // non-JSON error body — keep the status message
    }
    const err = new Error(detail) as Error & { status?: number };
    err.status = resp.status;
    throw err;
  }
  return (expectBody ? ((await resp.json()) as T) : (undefined as T));
}

export function login(
  email: string,
  password: string,
  fetchImpl: typeof fetch = fetch,
): Promise<TokenResponse> {
  return request<TokenResponse>(
    "/api/auth/login",
    { method: "POST", body: JSON.stringify({ email, password }) },
    null,
    fetchImpl,
  );
}

export function loginGoogle(
  idToken: string,
  fetchImpl: typeof fetch = fetch,
): Promise<TokenResponse> {
  return request<TokenResponse>(
    "/api/auth/google",
    { method: "POST", body: JSON.stringify({ id_token: idToken }) },
    null,
    fetchImpl,
  );
}

export interface RegisterInput {
  email: string;
  full_name?: string;
  password: string;
  tenant_slug: string;
}

/** Public self-service signup. Always provisions a plain attendee. */
export function registerPublic(
  input: RegisterInput,
  fetchImpl: typeof fetch = fetch,
): Promise<TokenResponse> {
  return request<TokenResponse>(
    "/api/auth/register",
    { method: "POST", body: JSON.stringify(input) },
    null,
    fetchImpl,
  );
}

export function getAuthConfig(fetchImpl: typeof fetch = fetch): Promise<AuthConfig> {
  return request<AuthConfig>("/api/auth/config", { method: "GET" }, null, fetchImpl);
}

export function getMe(token: string, fetchImpl: typeof fetch = fetch): Promise<CurrentUser> {
  return request<CurrentUser>("/api/auth/me", { method: "GET" }, token, fetchImpl);
}

export function listUsers(
  token: string,
  fetchImpl: typeof fetch = fetch,
): Promise<ManagedUser[]> {
  return request<ManagedUser[]>("/api/auth/users", { method: "GET" }, token, fetchImpl);
}

export function createManagedUser(
  token: string,
  input: NewUserInput,
  fetchImpl: typeof fetch = fetch,
): Promise<ManagedUser> {
  return request<ManagedUser>(
    "/api/auth/users",
    { method: "POST", body: JSON.stringify(input) },
    token,
    fetchImpl,
  );
}
