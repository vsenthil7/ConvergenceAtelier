import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { HackathonPanel } from "../components/HackathonPanel";

const team = {
  id: "t1",
  event_id: "e1",
  name: "Falcons",
  members: [{ user_id: "u1", email: "a@x.com", full_name: "A" }],
};

const leaderboardRow = {
  team_id: "t1",
  team_name: "Falcons",
  submission_id: "s1",
  submission_title: "ChronoSync",
  status: "submitted",
  total_score: 17,
  average_score: 8.5,
  score_count: 2,
  rank: 1,
};

/** Mutable mock store so create/join/submit reflect in subsequent reads. */
function makeFetch(opts: { withData?: boolean; failCreate?: boolean } = {}) {
  let teams = opts.withData ? [team] : [];
  let board = opts.withData ? [leaderboardRow] : [];
  return vi.fn(async (url: string, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    if (url.includes("/leaderboard")) {
      return { ok: true, status: 200, json: async () => board };
    }
    if (url.includes("/teams") && method === "GET") {
      return { ok: true, status: 200, json: async () => teams };
    }
    if (url.match(/\/teams\/[^/]+\/join/)) {
      return { ok: true, status: 200, json: async () => team };
    }
    if (url.match(/\/teams\/[^/]+\/submission/)) {
      return { ok: true, status: 201, json: async () => ({
        id: "s1", team_id: "t1", title: "ChronoSync", summary: "", repo_url: "", demo_url: "", status: "draft",
      }) };
    }
    if (url.endsWith("/teams") && method === "POST") {
      if (opts.failCreate) {
        return { ok: false, status: 409, json: async () => ({ detail: "Team Falcons already exists" }) };
      }
      const created = { ...team, id: "t2", name: "Eagles", members: [] };
      teams = [...teams, created];
      board = [...board];
      return { ok: true, status: 201, json: async () => created };
    }
    return { ok: false, status: 404, json: async () => ({ detail: "nope" }) };
  }) as unknown as typeof fetch;
}

describe("HackathonPanel", () => {
  it("shows empty states when there is no data (functional)", async () => {
    const f = makeFetch({});
    render(<HackathonPanel eventId="e1" fetchImpl={f} />);
    expect(await screen.findByTestId("teams-empty")).toBeInTheDocument();
    expect(screen.getByTestId("leaderboard-empty")).toBeInTheDocument();
  });

  it("renders teams and a live leaderboard (functional)", async () => {
    const f = makeFetch({ withData: true });
    render(<HackathonPanel eventId="e1" fetchImpl={f} />);
    // the join button for the team is unambiguous proof the team rendered
    expect(await screen.findByTestId("join-t1")).toBeInTheDocument();
    const grid = await screen.findByTestId("leaderboard-grid");
    expect(within(grid).getByText("ChronoSync")).toBeInTheDocument();
  });

  it("creates a team and refreshes the list (functional)", async () => {
    const f = makeFetch({});
    render(<HackathonPanel eventId="e1" fetchImpl={f} />);
    await screen.findByTestId("teams-empty");
    await userEvent.type(screen.getByLabelText("new-team-name"), "Eagles");
    await userEvent.click(screen.getByTestId("create-team"));
    // the newly created team (id t2) gets its own join button after refresh
    await waitFor(() => expect(screen.getByTestId("join-t2")).toBeInTheDocument());
  });

  it("disables create until a name is typed (negative)", async () => {
    const f = makeFetch({});
    render(<HackathonPanel eventId="e1" fetchImpl={f} />);
    await screen.findByTestId("teams-empty");
    expect(screen.getByTestId("create-team")).toBeDisabled();
  });

  it("joins a team (functional)", async () => {
    const f = makeFetch({ withData: true });
    render(<HackathonPanel eventId="e1" fetchImpl={f} />);
    const join = await screen.findByTestId("join-t1");
    await userEvent.click(join);
    // refresh re-fetches; the team's join button is still present
    await waitFor(() => expect(screen.getByTestId("join-t1")).toBeInTheDocument());
  });

  it("submits a project for a selected team (functional)", async () => {
    const f = makeFetch({ withData: true });
    render(<HackathonPanel eventId="e1" fetchImpl={f} />);
    await screen.findByTestId("hackathon-teams");
    await userEvent.selectOptions(screen.getByLabelText("submission-team"), "t1");
    await userEvent.type(screen.getByLabelText("submission-title"), "ChronoSync");
    expect(screen.getByTestId("submit-project")).not.toBeDisabled();
    await userEvent.click(screen.getByTestId("submit-project"));
    await waitFor(() => expect(screen.getByLabelText("submission-title")).toHaveValue(""));
  });

  it("keeps submit disabled without a team or title (negative)", async () => {
    const f = makeFetch({ withData: true });
    render(<HackathonPanel eventId="e1" fetchImpl={f} />);
    await screen.findByTestId("hackathon-teams");
    // title typed but no team selected
    await userEvent.type(screen.getByLabelText("submission-title"), "X");
    expect(screen.getByTestId("submit-project")).toBeDisabled();
  });

  it("surfaces an error when team creation fails (negative)", async () => {
    const f = makeFetch({ failCreate: true });
    render(<HackathonPanel eventId="e1" fetchImpl={f} />);
    await screen.findByTestId("teams-empty");
    await userEvent.type(screen.getByLabelText("new-team-name"), "Falcons");
    await userEvent.click(screen.getByTestId("create-team"));
    expect(await screen.findByTestId("hackathon-error")).toHaveTextContent("already exists");
  });

  it("surfaces an error when project submission fails (negative)", async () => {
    // teams load, but the submission POST errors
    const f = vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      if (url.includes("/leaderboard")) return { ok: true, status: 200, json: async () => [] };
      if (url.includes("/teams") && method === "GET")
        return { ok: true, status: 200, json: async () => [team] };
      if (url.match(/\/teams\/[^/]+\/submission/))
        return { ok: false, status: 409, json: async () => ({ detail: "Submission already exists" }) };
      return { ok: false, status: 404, json: async () => ({ detail: "nope" }) };
    }) as unknown as typeof fetch;
    render(<HackathonPanel eventId="e1" fetchImpl={f} />);
    await screen.findByTestId("hackathon-teams");
    await userEvent.selectOptions(screen.getByLabelText("submission-team"), "t1");
    await userEvent.type(screen.getByLabelText("submission-title"), "Dup");
    await userEvent.click(screen.getByTestId("submit-project"));
    expect(await screen.findByTestId("hackathon-error")).toHaveTextContent("already exists");
  });

  it("surfaces an error when loading fails (negative)", async () => {
    const f = vi.fn(async () => ({
      ok: false,
      status: 500,
      json: async () => ({ detail: "boom" }),
    })) as unknown as typeof fetch;
    render(<HackathonPanel eventId="e1" fetchImpl={f} />);
    expect(await screen.findByTestId("hackathon-error")).toBeInTheDocument();
  });
});
