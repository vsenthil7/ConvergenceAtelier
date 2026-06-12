import { useCallback, useEffect, useState } from "react";
import { Grid, GridColumn } from "@progress/kendo-react-grid";
import { Input } from "@progress/kendo-react-inputs";
import { Button } from "@progress/kendo-react-buttons";
import {
  listTeams,
  createTeam,
  joinTeam,
  createSubmission,
  getLeaderboard,
  type Team,
  type LeaderboardRow,
} from "../lib/hackathon";

interface Props {
  eventId: string;
  fetchImpl?: typeof fetch;
}

/**
 * Hackathon workspace shown when an event's type is "hackathon" (S7.3):
 * team list with join, a create-team + submission form, and a live leaderboard.
 */
export function HackathonPanel({ eventId, fetchImpl = fetch }: Props) {
  const [teams, setTeams] = useState<Team[]>([]);
  const [board, setBoard] = useState<LeaderboardRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // form state
  const [teamName, setTeamName] = useState("");
  const [selectedTeam, setSelectedTeam] = useState<string>("");
  const [subTitle, setSubTitle] = useState("");
  const [subRepo, setSubRepo] = useState("");
  const [subDemo, setSubDemo] = useState("");

  const refresh = useCallback(async () => {
    try {
      const [t, b] = await Promise.all([
        listTeams(eventId, fetchImpl),
        getLeaderboard(eventId, fetchImpl),
      ]);
      setTeams(t);
      setBoard(b);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load hackathon data");
    }
  }, [eventId, fetchImpl]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleCreateTeam = async () => {
    if (!teamName.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const team = await createTeam(eventId, teamName.trim(), fetchImpl);
      setTeamName("");
      setSelectedTeam(team.id);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create team");
    } finally {
      setBusy(false);
    }
  };

  const handleJoin = async (teamId: string) => {
    setBusy(true);
    try {
      await joinTeam(eventId, teamId, fetchImpl);
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  const handleSubmit = async () => {
    if (!selectedTeam || !subTitle.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await createSubmission(
        eventId,
        selectedTeam,
        { title: subTitle.trim(), repo_url: subRepo.trim(), demo_url: subDemo.trim() },
        fetchImpl,
      );
      setSubTitle("");
      setSubRepo("");
      setSubDemo("");
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not submit project");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="hackathon" data-testid="hackathon-panel">
      <h3>Hackathon</h3>

      {error && (
        <p role="alert" data-testid="hackathon-error" className="hackathon-error">
          {error}
        </p>
      )}

      <div className="hackathon-cols">
        <div className="hackathon-teams" data-testid="hackathon-teams">
          <h4>Teams ({teams.length})</h4>
          {teams.length === 0 ? (
            <p data-testid="teams-empty">No teams yet — be the first to form one.</p>
          ) : (
            <ul className="team-list">
              {teams.map((t) => (
                <li key={t.id}>
                  <span className="team-name">{t.name}</span>{" "}
                  <span className="team-count">({t.members.length} members)</span>{" "}
                  <Button
                    fillMode="flat"
                    onClick={() => void handleJoin(t.id)}
                    disabled={busy}
                    data-testid={`join-${t.id}`}
                  >
                    Join
                  </Button>
                </li>
              ))}
            </ul>
          )}

          <div className="hackathon-create">
            <Input
              value={teamName}
              onChange={(e) => setTeamName(String(e.value))}
              aria-label="new-team-name"
              placeholder="New team name"
            />
            <Button
              themeColor="primary"
              onClick={() => void handleCreateTeam()}
              disabled={busy || !teamName.trim()}
              data-testid="create-team"
            >
              Create team
            </Button>
          </div>

          <div className="hackathon-submit">
            <h4>Submit a project</h4>
            <label>
              Team
              <select
                aria-label="submission-team"
                value={selectedTeam}
                onChange={(e) => setSelectedTeam(e.target.value)}
                className="k-input k-input-md k-rounded-md k-input-solid"
              >
                <option value="">Select a team…</option>
                {teams.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </label>
            <Input
              value={subTitle}
              onChange={(e) => setSubTitle(String(e.value))}
              aria-label="submission-title"
              placeholder="Project title"
            />
            <Input
              value={subRepo}
              onChange={(e) => setSubRepo(String(e.value))}
              aria-label="submission-repo"
              placeholder="Repo URL"
            />
            <Input
              value={subDemo}
              onChange={(e) => setSubDemo(String(e.value))}
              aria-label="submission-demo"
              placeholder="Demo URL"
            />
            <Button
              themeColor="primary"
              onClick={() => void handleSubmit()}
              disabled={busy || !selectedTeam || !subTitle.trim()}
              data-testid="submit-project"
            >
              Submit project
            </Button>
          </div>
        </div>

        <div className="hackathon-leaderboard" data-testid="hackathon-leaderboard">
          <h4>Live leaderboard</h4>
          {board.length === 0 ? (
            <p data-testid="leaderboard-empty">No submissions scored yet.</p>
          ) : (
            <div data-testid="leaderboard-grid">
              <Grid data={board} scrollable="none">
                <GridColumn field="rank" title="#" width="60px" />
                <GridColumn field="submission_title" title="Project" />
                <GridColumn field="team_name" title="Team" />
                <GridColumn field="total_score" title="Total" width="90px" />
                <GridColumn field="average_score" title="Avg" width="90px" />
              </Grid>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
