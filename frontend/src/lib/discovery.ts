// Typed client for the AI discovery API (S3).
// Pure functions with an injectable fetch so every path is unit-testable.

import type { AgendaSession } from "./events";

export interface ScoredSession {
  score: number;
  session: AgendaSession;
}

export interface AttendeeProfileInput {
  id: string;
  name?: string;
  interests?: string;
}

export interface AttendeeRef {
  id: string;
  name: string;
}

export interface AttendeeMatch {
  score: number;
  a: AttendeeRef;
  b: AttendeeRef;
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
      // non-JSON error body — keep the status message
    }
    const err = new Error(detail) as Error & { status?: number };
    err.status = resp.status;
    throw err;
  }
  return (await resp.json()) as T;
}

export function similarSessions(
  sessionId: string,
  limit = 5,
  fetchImpl: typeof fetch = fetch,
): Promise<ScoredSession[]> {
  return request<ScoredSession[]>(
    `/api/discovery/sessions/${sessionId}/similar?limit=${limit}`,
    { method: "GET" },
    fetchImpl,
  );
}

export function recommendForInterests(
  interests: string,
  limit = 5,
  fetchImpl: typeof fetch = fetch,
): Promise<ScoredSession[]> {
  return request<ScoredSession[]>(
    "/api/discovery/recommend",
    { method: "POST", body: JSON.stringify({ interests, limit }) },
    fetchImpl,
  );
}

export function matchAttendees(
  attendees: AttendeeProfileInput[],
  limit = 5,
  fetchImpl: typeof fetch = fetch,
): Promise<AttendeeMatch[]> {
  return request<AttendeeMatch[]>(
    "/api/discovery/match",
    { method: "POST", body: JSON.stringify({ attendees, limit }) },
    fetchImpl,
  );
}
