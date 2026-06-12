import { useEffect, useState } from "react";
import { Grid, GridColumn, type GridCustomCellProps } from "@progress/kendo-react-grid";
import { Input } from "@progress/kendo-react-inputs";
import { Button } from "@progress/kendo-react-buttons";
import { Loader } from "@progress/kendo-react-indicators";
import {
  draftAgenda,
  recommendForInterests,
  type AgendaSlot,
  type ScoredSession,
} from "../lib/discovery";
import { listEvents, type EventModel } from "../lib/events";

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

  // --- AI agenda draft state ---
  const [events, setEvents] = useState<EventModel[]>([]);
  const [eventId, setEventId] = useState("");
  const [theme, setTheme] = useState("");
  const [draft, setDraft] = useState<AgendaSlot[] | null>(null);
  const [draftLoading, setDraftLoading] = useState(false);
  const [draftError, setDraftError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listEvents(fetchImpl)
      .then((evs) => {
        if (cancelled) return;
        setEvents(evs);
        if (evs.length > 0) setEventId(evs[0].id);
      })
      .catch(() => {
        if (!cancelled) setEvents([]);
      });
    return () => {
      cancelled = true;
    };
  }, [fetchImpl]);

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

  const makeDraft = async () => {
    setDraftLoading(true);
    setDraftError(null);
    try {
      setDraft(await draftAgenda(eventId, theme, fetchImpl));
    } catch (e) {
      setDraftError(e instanceof Error ? e.message : "Agenda draft failed");
      setDraft(null);
    } finally {
      setDraftLoading(false);
    }
  };

  const canSearch = interests.trim().length > 0 && !loading;
  const canDraft = theme.trim().length > 0 && eventId.length > 0 && !draftLoading;

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

      <hr className="discovery-divider" />

      <h2>AI agenda draft</h2>
      <p className="discovery-sub">
        Pick an event and a theme — we&apos;ll suggest a running order, grouping
        talks by track and opening with the most on-theme track.
      </p>

      <div className="discovery-draft-controls">
        <label className="discovery-field">
          Event
          <select
            aria-label="agenda-event"
            value={eventId}
            onChange={(e) => setEventId(e.target.value)}
          >
            {events.length === 0 && <option value="">No events available</option>}
            {events.map((ev) => (
              <option key={ev.id} value={ev.id}>
                {ev.name}
              </option>
            ))}
          </select>
        </label>
        <Input
          value={theme}
          onChange={(e) => setTheme(String(e.value))}
          aria-label="agenda-theme"
          placeholder="e.g. the future of frontend performance"
        />
        <Button
          themeColor="primary"
          onClick={() => void makeDraft()}
          disabled={!canDraft}
          data-testid="agenda-draft-go"
        >
          Draft agenda
        </Button>
      </div>

      {draftLoading && <Loader type="infinite-spinner" />}
      {draftError && (
        <p role="alert" data-testid="agenda-draft-error">
          {draftError}
        </p>
      )}

      {!draftLoading && !draftError && draft !== null && draft.length === 0 && (
        <p data-testid="agenda-draft-empty">
          This event has no sessions to arrange yet.
        </p>
      )}

      {!draftLoading && !draftError && draft !== null && draft.length > 0 && (
        <ol className="agenda-draft-list" data-testid="agenda-draft-results">
          {draft.map((slot) => (
            <li key={slot.session.id} className="agenda-draft-slot">
              <span className="agenda-draft-track">{slot.track}</span>
              <span className="agenda-draft-title">{slot.session.title}</span>
              <span className="agenda-draft-speaker">
                {slot.session.speaker || "TBA"}
              </span>
              <span
                className="discovery-score"
                aria-label={`relevance-${Math.round(slot.relevance * 100)}`}
              >
                {Math.round(slot.relevance * 100)}%
              </span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
