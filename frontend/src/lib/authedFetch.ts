// Wraps a fetch implementation so every request carries the bearer token.
// Lets existing token-agnostic API clients (events.ts) stay unchanged while the
// app is authenticated.

export function makeAuthedFetch(
  token: string | null,
  baseFetch: typeof fetch = fetch,
): typeof fetch {
  const authed = (input: RequestInfo | URL, init?: RequestInit) => {
    const headers = new Headers(init?.headers ?? {});
    if (token) headers.set("Authorization", `Bearer ${token}`);
    return baseFetch(input, { ...init, headers });
  };
  return authed as typeof fetch;
}
