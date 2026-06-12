// Typed client for the events + agenda API (S1).
// Pure functions with an injectable fetch so every path is unit-testable.

export interface AgendaSession {
  id: string;
  event_id: string;
  title: string;
  track: string;
  speaker: string;
  starts_at: string;
  ends_at: string;
}

export interface EventModel {
  id: string;
  name: string;
  location: string;
  description: string;
  starts_at: string;
  ends_at: string;
  sessions: AgendaSession[];
}

export interface EventInput {
  name: string;
  location: string;
  description: string;
  starts_at: string;
  ends_at: string;
}

export interface SessionInput {
  title: string;
  track: string;
  speaker: string;
  starts_at: string;
  ends_at: string;
}

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

async function request<T>(
  path: string,
  init: RequestInit,
  fetchImpl: typeof fetch,
  expectBody = true,
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
  return (expectBody ? ((await resp.json()) as T) : (undefined as T));
}

export function listEvents(fetchImpl: typeof fetch = fetch): Promise<EventModel[]> {
  return request<EventModel[]>("/api/events", { method: "GET" }, fetchImpl);
}

export function createEvent(
  input: EventInput,
  fetchImpl: typeof fetch = fetch,
): Promise<EventModel> {
  return request<EventModel>(
    "/api/events",
    { method: "POST", body: JSON.stringify(input) },
    fetchImpl,
  );
}

export function updateEvent(
  id: string,
  input: Partial<EventInput>,
  fetchImpl: typeof fetch = fetch,
): Promise<EventModel> {
  return request<EventModel>(
    `/api/events/${id}`,
    { method: "PATCH", body: JSON.stringify(input) },
    fetchImpl,
  );
}

export function deleteEvent(id: string, fetchImpl: typeof fetch = fetch): Promise<void> {
  return request<void>(
    `/api/events/${id}`,
    { method: "DELETE" },
    fetchImpl,
    false,
  );
}

export function addSession(
  eventId: string,
  input: SessionInput,
  fetchImpl: typeof fetch = fetch,
): Promise<AgendaSession> {
  return request<AgendaSession>(
    `/api/events/${eventId}/sessions`,
    { method: "POST", body: JSON.stringify(input) },
    fetchImpl,
  );
}

// ---------- registration / participation (S3b) ----------

export type RegistrationStatus = "registered" | "cancelled";

export interface MyRegistration {
  event_id: string;
  status: RegistrationStatus | null;
}

export interface Participant {
  user_id: string;
  email: string;
  full_name: string;
  status: RegistrationStatus;
}

export function registerForEvent(
  eventId: string,
  fetchImpl: typeof fetch = fetch,
): Promise<{ status: RegistrationStatus }> {
  return request<{ status: RegistrationStatus }>(
    `/api/events/${eventId}/register`,
    { method: "POST" },
    fetchImpl,
  );
}

export function cancelRegistration(
  eventId: string,
  fetchImpl: typeof fetch = fetch,
): Promise<{ status: RegistrationStatus }> {
  return request<{ status: RegistrationStatus }>(
    `/api/events/${eventId}/register`,
    { method: "DELETE" },
    fetchImpl,
  );
}

export function myRegistration(
  eventId: string,
  fetchImpl: typeof fetch = fetch,
): Promise<MyRegistration> {
  return request<MyRegistration>(
    `/api/events/${eventId}/registration`,
    { method: "GET" },
    fetchImpl,
  );
}

export function eventParticipants(
  eventId: string,
  fetchImpl: typeof fetch = fetch,
): Promise<Participant[]> {
  return request<Participant[]>(
    `/api/events/${eventId}/participants`,
    { method: "GET" },
    fetchImpl,
  );
}
