// Typed client for the type-aware plan-draft API (S7.6).
// Self-contained request helper with an injectable fetch so every path is unit-testable.

export interface PlanItem {
  order: number;
  key: string;
  label: string;
  detail: string;
  target_at: string;
  relevance: number;
}

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

async function request<T>(
  path: string,
  init: RequestInit,
  fetchImpl: typeof fetch,
): Promise<T> {
  const resp = await fetchImpl(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!resp.ok) {
    let detail = `Request failed: ${resp.status}`;
    try {
      const body = await resp.json();
      if (body && typeof body.detail === "string") detail = body.detail;
    } catch {
      // non-JSON error body — keep the status-based message
    }
    throw new Error(detail);
  }
  return (await resp.json()) as T;
}

export function draftPlan(
  eventId: string,
  theme: string,
  fetchImpl: typeof fetch = fetch,
): Promise<PlanItem[]> {
  return request<PlanItem[]>(
    `/api/discovery/events/${eventId}/plan`,
    { method: "POST", body: JSON.stringify({ theme }) },
    fetchImpl,
  );
}
