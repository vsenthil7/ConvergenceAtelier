// Typed client for the hackathon module API (S7.3).
// Self-contained request helper with an injectable fetch so every path is unit-testable.

export type SubmissionStatus = "draft" | "submitted" | "disqualified";

export interface TeamMember {
  user_id: string;
  email: string;
  full_name: string;
}

export interface Team {
  id: string;
  event_id: string;
  name: string;
  members: TeamMember[];
}

export interface Submission {
  id: string;
  team_id: string;
  title: string;
  summary: string;
  repo_url: string;
  demo_url: string;
  status: SubmissionStatus;
}

export interface SubmissionInput {
  title: string;
  summary?: string;
  repo_url?: string;
  demo_url?: string;
}

export interface LeaderboardRow {
  team_id: string;
  team_name: string;
  submission_id: string;
  submission_title: string;
  status: SubmissionStatus;
  total_score: number;
  average_score: number;
  score_count: number;
  rank: number;
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
  return `/api/events/${eventId}/hackathon`;
}

export function listTeams(
  eventId: string,
  fetchImpl: typeof fetch = fetch,
): Promise<Team[]> {
  return request<Team[]>(`${base(eventId)}/teams`, { method: "GET" }, fetchImpl);
}

export function createTeam(
  eventId: string,
  name: string,
  fetchImpl: typeof fetch = fetch,
): Promise<Team> {
  return request<Team>(
    `${base(eventId)}/teams`,
    { method: "POST", body: JSON.stringify({ name }) },
    fetchImpl,
  );
}

export function joinTeam(
  eventId: string,
  teamId: string,
  fetchImpl: typeof fetch = fetch,
): Promise<Team> {
  return request<Team>(
    `${base(eventId)}/teams/${teamId}/join`,
    { method: "POST" },
    fetchImpl,
  );
}

export function listSubmissions(
  eventId: string,
  fetchImpl: typeof fetch = fetch,
): Promise<Submission[]> {
  return request<Submission[]>(
    `${base(eventId)}/submissions`,
    { method: "GET" },
    fetchImpl,
  );
}

export function createSubmission(
  eventId: string,
  teamId: string,
  input: SubmissionInput,
  fetchImpl: typeof fetch = fetch,
): Promise<Submission> {
  return request<Submission>(
    `${base(eventId)}/teams/${teamId}/submission`,
    { method: "POST", body: JSON.stringify(input) },
    fetchImpl,
  );
}

export function updateSubmission(
  eventId: string,
  submissionId: string,
  input: Partial<SubmissionInput> & { status?: SubmissionStatus },
  fetchImpl: typeof fetch = fetch,
): Promise<Submission> {
  return request<Submission>(
    `${base(eventId)}/submissions/${submissionId}`,
    { method: "PATCH", body: JSON.stringify(input) },
    fetchImpl,
  );
}

export function getLeaderboard(
  eventId: string,
  fetchImpl: typeof fetch = fetch,
): Promise<LeaderboardRow[]> {
  return request<LeaderboardRow[]>(
    `${base(eventId)}/leaderboard`,
    { method: "GET" },
    fetchImpl,
  );
}
