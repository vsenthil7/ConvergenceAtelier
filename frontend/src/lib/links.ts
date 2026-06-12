// Typed client for the event-links module API (S7.5).
// Self-contained request helper with an injectable fetch so every path is unit-testable.

export type EventType =
  | "conference"
  | "hackathon"
  | "webinar"
  | "meetup"
  | "workshop"
  | "hybrid";

export interface LinkedEvent {
  id: string;
  name: string;
  location: string;
  event_type: EventType;
  starts_at: string;
  ends_at: string;
}

export interface CatalogSession {
  session_id: string;
  event_id: string;
  event_name: string;
  title: string;
  track: string;
  speaker: string;
  mode: string;
  stream_url: string;
  recording_url: string;
  starts_at: string;
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

function base(eventId: string): string {
  return `/api/events/${eventId}`;
}

export function listLinks(
  eventId: string,
  fetchImpl: typeof fetch = fetch,
): Promise<LinkedEvent[]> {
  return request<LinkedEvent[]>(`${base(eventId)}/links`, { method: "GET" }, fetchImpl);
}

export function linkEvent(
  eventId: string,
  otherEventId: string,
  fetchImpl: typeof fetch = fetch,
): Promise<LinkedEvent[]> {
  return request<LinkedEvent[]>(
    `${base(eventId)}/links`,
    { method: "POST", body: JSON.stringify({ other_event_id: otherEventId }) },
    fetchImpl,
  );
}

export function unlinkEvent(
  eventId: string,
  otherEventId: string,
  fetchImpl: typeof fetch = fetch,
): Promise<LinkedEvent[]> {
  return request<LinkedEvent[]>(
    `${base(eventId)}/links/${otherEventId}`,
    { method: "DELETE" },
    fetchImpl,
  );
}

export function combinedCatalog(
  eventId: string,
  fetchImpl: typeof fetch = fetch,
): Promise<CatalogSession[]> {
  return request<CatalogSession[]>(`${base(eventId)}/catalog`, { method: "GET" }, fetchImpl);
}
