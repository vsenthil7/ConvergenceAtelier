// Thin API client for the Convergence Atelier backend.
// Centralises base URL + error handling so components stay clean and testable.

export interface HealthStatus {
  status: string;
  service: string;
  version: string;
  mode: "mock" | "live";
  time: string;
}

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export async function getHealth(
  fetchImpl: typeof fetch = fetch,
): Promise<HealthStatus> {
  const resp = await fetchImpl(`${API_BASE}/api/health`);
  if (!resp.ok) {
    throw new Error(`Health check failed: ${resp.status}`);
  }
  return (await resp.json()) as HealthStatus;
}
