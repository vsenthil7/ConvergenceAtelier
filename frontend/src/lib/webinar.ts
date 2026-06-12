// Typed client for the webinar module API (S7.4).
// Self-contained request helper with an injectable fetch so every path is unit-testable.

export type RegistrationStatus = "registered" | "cancelled" | "waitlisted";

export interface WebinarStatus {
  event_id: string;
  capacity: number; // 0 = unlimited
  registered_count: number;
  waitlisted_count: number;
  seats_left: number | null; // null when unlimited
  my_state: RegistrationStatus | null;
  stream_url: string;
}

export interface WaitlistEntry {
  user_id: string;
  email: string;
  full_name: string;
  position: number;
}

export interface Reminder {
  offset: string;
  send_at: string;
}

export interface WebinarRegistration {
  event_id: string;
  status: RegistrationStatus;
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
  return `/api/events/${eventId}/webinar`;
}

export function webinarStatus(
  eventId: string,
  fetchImpl: typeof fetch = fetch,
): Promise<WebinarStatus> {
  return request<WebinarStatus>(`${base(eventId)}/status`, { method: "GET" }, fetchImpl);
}

export function webinarRegister(
  eventId: string,
  fetchImpl: typeof fetch = fetch,
): Promise<WebinarRegistration> {
  return request<WebinarRegistration>(
    `${base(eventId)}/register`,
    { method: "POST" },
    fetchImpl,
  );
}

export function webinarCancel(
  eventId: string,
  fetchImpl: typeof fetch = fetch,
): Promise<WebinarRegistration> {
  return request<WebinarRegistration>(
    `${base(eventId)}/register`,
    { method: "DELETE" },
    fetchImpl,
  );
}

export function webinarWaitlist(
  eventId: string,
  fetchImpl: typeof fetch = fetch,
): Promise<WaitlistEntry[]> {
  return request<WaitlistEntry[]>(`${base(eventId)}/waitlist`, { method: "GET" }, fetchImpl);
}

export function webinarReminders(
  eventId: string,
  fetchImpl: typeof fetch = fetch,
): Promise<Reminder[]> {
  return request<Reminder[]>(`${base(eventId)}/reminders`, { method: "GET" }, fetchImpl);
}
