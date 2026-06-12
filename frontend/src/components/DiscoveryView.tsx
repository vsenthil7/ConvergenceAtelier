import { useState } from "react";
import { Grid, GridColumn, type GridCustomCellProps } from "@progress/kendo-react-grid";
import { Input } from "@progress/kendo-react-inputs";
import { Button } from "@progress/kendo-react-buttons";
import { Loader } from "@progress/kendo-react-indicators";
import {
  recommendForInterests,
  type ScoredSession,
} from "../lib/discovery";

interface Props {
  fetchImpl?: typeof fetch;
}

/** Render the 0..1 score as a percentage badge. */
function ScoreCell(props: GridCustomCellProps) {
  const row = props.dataItem as ScoredSession;
  const pct = Math.round(row.score * 100);
  return (
    <td {...props.tdProps}>
      <span className="discovery-score" aria-label={`match-${pct}`}>
        {pct}%
      </span>
    </td>
  );
}

function TitleCell(props: GridCustomCellProps) {
  const row = props.dataItem as ScoredSession;
  return <td {...props.tdProps}>{row.session.title}</td>;
}

function TrackCell(props: GridCustomCellProps) {
  const row = props.dataItem as ScoredSession;
  return <td {...props.tdProps}>{row.session.track}</td>;
}

function SpeakerCell(props: GridCustomCellProps) {
  const row = props.dataItem as ScoredSession;
  return <td {...props.tdProps}>{row.session.speaker || "TBA"}</td>;
}

export function DiscoveryView({ fetchImpl = fetch }: Props) {
  const [interests, setInterests] = useState("");
  const [results, setResults] = useState<ScoredSession[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const search = async () => {
    setLoading(true);
    setError(null);
    try {
      setResults(await recommendForInterests(interests, 10, fetchImpl));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Recommendation failed");
      setResults(null);
    } finally {
      setLoading(false);
    }
  };

  const canSearch = interests.trim().length > 0 && !loading;

  return (
    <section className="discovery-view">
      <h2>Discover talks</h2>
      <p className="discovery-sub">
        Describe what you&apos;re into and we&apos;ll rank the agenda by relevance.
      </p>

      <div className="discovery-search">
        <Input
          value={interests}
          onChange={(e) => setInterests(String(e.value))}
          aria-label="discovery-interests"
          placeholder="e.g. react performance, state management, testing"
        />
        <Button
          themeColor="primary"
          onClick={() => void search()}
          disabled={!canSearch}
          data-testid="discovery-search"
        >
          Recommend
        </Button>
      </div>

      {loading && <Loader type="infinite-spinner" />}
      {error && (
        <p role="alert" data-testid="discovery-error">
          {error}
        </p>
      )}

      {!loading && !error && results !== null && results.length === 0 && (
        <p data-testid="discovery-empty">
          No sessions to recommend yet — add some talks to the agenda first.
        </p>
      )}

      {!loading && !error && results !== null && results.length > 0 && (
        <div data-testid="discovery-results">
          <Grid data={results} scrollable="none">
            <GridColumn title="Match" cells={{ data: ScoreCell }} width="90px" />
            <GridColumn title="Talk" cells={{ data: TitleCell }} />
            <GridColumn title="Track" cells={{ data: TrackCell }} />
            <GridColumn title="Speaker" cells={{ data: SpeakerCell }} />
          </Grid>
        </div>
      )}
    </section>
  );
}
