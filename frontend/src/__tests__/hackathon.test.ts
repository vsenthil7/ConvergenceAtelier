import { describe, it, expect, vi } from "vitest";
import {
  listTeams,
  createTeam,
  joinTeam,
  listSubmissions,
  createSubmission,
  updateSubmission,
  getLeaderboard,
} from "../lib/hackathon";

function fetchReturning(status: number, body: unknown, ok = status < 400): typeof fetch {
  return vi.fn(async () => ({ ok, status, json: async () => body })) as unknown as typeof fetch;
}

const team = {
  id: "t1",
  event_id: "e1",
  name: "Falcons",
  members: [{ user_id: "u1", email: "a@x.com", full_name: "A" }],
};

const submission = {
  id: "s1",
  team_id: "t1",
  title: "ChronoSync",
  summary: "",
  repo_url: "https://github.com/x/y",
  demo_url: "",
  status: "draft",
};

describe("hackathon api client", () => {
  it("lists teams (functional)", async () => {
    const f = fetchReturning(200, [team]);
    const out = await listTeams("e1", f);
    expect(out).toHaveLength(1);
    expect(out[0].name).toBe("Falcons");
  });

  it("creates a team and sends the name (functional)", async () => {
    const spy = vi.fn(async () => ({ ok: true, status: 201, json: async () => team }));
    const out = await createTeam("e1", "Falcons", spy as unknown as typeof fetch);
    expect(out.id).toBe("t1");
    expect(spy.mock.calls[0][0]).toContain("/api/events/e1/hackathon/teams");
    expect(JSON.parse(String((spy.mock.calls[0][1] as RequestInit).body)).name).toBe("Falcons");
  });

  it("joins a team (functional)", async () => {
    const spy = vi.fn(async () => ({ ok: true, status: 200, json: async () => team }));
    await joinTeam("e1", "t1", spy as unknown as typeof fetch);
    expect(spy.mock.calls[0][0]).toContain("/api/events/e1/hackathon/teams/t1/join");
    expect((spy.mock.calls[0][1] as RequestInit).method).toBe("POST");
  });

  it("lists submissions (functional)", async () => {
    const f = fetchReturning(200, [submission]);
    const out = await listSubmissions("e1", f);
    expect(out[0].title).toBe("ChronoSync");
  });

  it("creates a submission (functional)", async () => {
    const spy = vi.fn(async () => ({ ok: true, status: 201, json: async () => submission }));
    const out = await createSubmission(
      "e1",
      "t1",
      { title: "ChronoSync", repo_url: "https://github.com/x/y" },
      spy as unknown as typeof fetch,
    );
    expect(out.status).toBe("draft");
    expect(spy.mock.calls[0][0]).toContain("/api/events/e1/hackathon/teams/t1/submission");
  });

  it("updates a submission (functional)", async () => {
    const spy = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({ ...submission, status: "submitted" }),
    }));
    const out = await updateSubmission(
      "e1",
      "s1",
      { status: "submitted" },
      spy as unknown as typeof fetch,
    );
    expect(out.status).toBe("submitted");
    expect((spy.mock.calls[0][1] as RequestInit).method).toBe("PATCH");
  });

  it("gets the leaderboard (functional)", async () => {
    const f = fetchReturning(200, [
      {
        team_id: "t1", team_name: "Falcons", submission_id: "s1",
        submission_title: "ChronoSync", status: "submitted",
        total_score: 17, average_score: 8.5, score_count: 2, rank: 1,
      },
    ]);
    const out = await getLeaderboard("e1", f);
    expect(out[0].rank).toBe(1);
    expect(out[0].total_score).toBe(17);
  });

  it("throws API detail on error (negative)", async () => {
    const f = fetchReturning(409, { detail: "Team Falcons already exists" }, false);
    await expect(createTeam("e1", "Falcons", f)).rejects.toThrow("Team Falcons already exists");
  });

  it("falls back to status message on non-JSON error (negative)", async () => {
    const f = vi.fn(async () => ({
      ok: false,
      status: 500,
      json: async () => {
        throw new Error("not json");
      },
    })) as unknown as typeof fetch;
    await expect(listTeams("e1", f)).rejects.toThrow("Request failed: 500");
  });
});
