import { useCallback, useEffect, useState } from "react";
import { Grid, GridColumn, type GridCustomCellProps } from "@progress/kendo-react-grid";
import { Scheduler, DayView, WeekView } from "@progress/kendo-react-scheduler";
import { Dialog } from "@progress/kendo-react-dialogs";
import { Button } from "@progress/kendo-react-buttons";
import { Loader } from "@progress/kendo-react-indicators";
import {
  listEvents,
  createEvent,
  deleteEvent,
  registerForEvent,
  cancelRegistration,
  myRegistration,
  eventParticipants,
  eventRecordings,
  type EventModel,
  type EventInput,
  type Participant,
  type RegistrationStatus,
  type AgendaSession,
  type SessionMode,
} from "../lib/events";
import { EventForm } from "./EventForm";
import { HackathonPanel } from "./HackathonPanel";
import { WebinarPanel } from "./WebinarPanel";
import { LinkedEventsPanel } from "./LinkedEventsPanel";
import { PlanPanel } from "./PlanPanel";

const MODE_LABEL: Record<SessionMode, string> = {
  in_person: "In person",
  online: "Online",
  hybrid: "Hybrid",
};

interface Deps {
  fetchImpl?: typeof fetch;
  /** Sensible default window for the new-event form (overridable for tests). */
  newEventDefaults?: Partial<EventInput>;
  /** When false, hides create/delete controls (attendee role). Defaults true. */
  canWrite?: boolean;
}

function defaultWindow(): Partial<EventInput> {
  const start = new Date();
  start.setMinutes(0, 0, 0);
  const end = new Date(start.getTime() + 8 * 60 * 60 * 1000);
  return { starts_at: start.toISOString(), ends_at: end.toISOString() };
}

export function EventsView({ fetchImpl = fetch, newEventDefaults, canWrite = true }: Deps) {
  const [events, setEvents] = useState<EventModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Participation state (S3b). canWrite distinguishes admin (roster) from attendee (register).
  const [myStatus, setMyStatus] = useState<RegistrationStatus | null>(null);
  const [roster, setRoster] = useState<Participant[]>([]);
  const [regBusy, setRegBusy] = useState(false);
  // Recordings catalog (S7.2): sessions in the selected event that have a recording.
  const [recordings, setRecordings] = useState<AgendaSession[]>([]);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listEvents(fetchImpl);
      setEvents(data);
      if (data.length && selectedId === null) setSelectedId(data[0].id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load events");
    } finally {
      setLoading(false);
    }
  }, [fetchImpl, selectedId]);

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCreate = async (input: EventInput) => {
    const created = await createEvent(input, fetchImpl);
    setShowForm(false);
    setSelectedId(created.id);
    await refresh();
  };

  const handleDelete = async (id: string) => {
    await deleteEvent(id, fetchImpl);
    if (selectedId === id) setSelectedId(null);
    await refresh();
  };

  // Load participation context whenever the selected event changes.
  const loadParticipation = useCallback(
    async (eventId: string) => {
      if (canWrite) {
        try {
          setRoster(await eventParticipants(eventId, fetchImpl));
        } catch {
          setRoster([]);
        }
      } else {
        try {
          const mine = await myRegistration(eventId, fetchImpl);
          setMyStatus(mine.status);
        } catch {
          setMyStatus(null);
        }
      }
      // Recordings catalog is visible to every role.
      try {
        setRecordings(await eventRecordings(eventId, fetchImpl));
      } catch {
        setRecordings([]);
      }
    },
    [canWrite, fetchImpl],
  );

  useEffect(() => {
    if (selectedId) void loadParticipation(selectedId);
  }, [selectedId, loadParticipation]);

  const toggleRegistration = async () => {
    if (!selectedId) return;
    setRegBusy(true);
    try {
      if (myStatus === "registered") {
        const res = await cancelRegistration(selectedId, fetchImpl);
        setMyStatus(res.status);
      } else {
        const res = await registerForEvent(selectedId, fetchImpl);
        setMyStatus(res.status);
      }
    } finally {
      setRegBusy(false);
    }
  };

  const TypeCell = (props: GridCustomCellProps) => {
    const row = props.dataItem as EventModel;
    return (
      <td {...props.tdProps}>
        <span className={`event-type-badge event-type-${row.event_type}`}>
          {row.event_type}
        </span>
      </td>
    );
  };

  const ActionsCell = (props: GridCustomCellProps) => {
    const row = props.dataItem as EventModel;
    return (
      <td {...props.tdProps}>
        <Button
          fillMode="flat"
          onClick={() => setSelectedId(row.id)}
          aria-label={`view-${row.id}`}
        >
          View agenda
        </Button>
        {canWrite && (
          <Button
            fillMode="flat"
            themeColor="error"
            onClick={() => void handleDelete(row.id)}
            aria-label={`delete-${row.id}`}
          >
            Delete
          </Button>
        )}
      </td>
    );
  };

  const selected = events.find((e) => e.id === selectedId) ?? null;
  const agendaItems =
    selected?.sessions.map((s) => ({
      id: s.id,
      title: `${s.title} — ${s.speaker || "TBA"}`,
      start: new Date(s.starts_at),
      end: new Date(s.ends_at),
    })) ?? [];

  return (
    <section className="events-view">
      <header className="events-view-header">
        <h2>Events</h2>
        {canWrite && (
          <Button themeColor="primary" onClick={() => setShowForm(true)} data-testid="new-event">
            New event
          </Button>
        )}
      </header>

      {loading && <Loader type="infinite-spinner" />}
      {error && (
        <p role="alert" data-testid="events-error">
          {error}
        </p>
      )}

      {!loading && !error && events.length === 0 && (
        <p data-testid="events-empty">No events yet. Create your first one.</p>
      )}

      {!loading && !error && events.length > 0 && (
        <div data-testid="events-grid">
          <Grid data={events} scrollable="none">
            <GridColumn field="name" title="Name" />
            <GridColumn title="Type" cells={{ data: TypeCell }} width="120px" />
            <GridColumn field="location" title="Location" />
            <GridColumn field="starts_at" title="Starts" />
            <GridColumn field="ends_at" title="Ends" />
            <GridColumn title="Actions" cells={{ data: ActionsCell }} />
          </Grid>
        </div>
      )}

      {selected && (
        <div className="agenda" data-testid="agenda">
          <h3>Agenda — {selected.name}</h3>

          {/* Participation (S3b): attendee registers; admin sees the roster. */}
          {!canWrite && (
            <div className="agenda-participation" data-testid="participation">
              <Button
                themeColor={myStatus === "registered" ? "base" : "primary"}
                onClick={() => void toggleRegistration()}
                disabled={regBusy}
                data-testid="register-toggle"
              >
                {myStatus === "registered" ? "Registered ✓ — Cancel" : "Register for this event"}
              </Button>
              {myStatus === "registered" && (
                <span className="agenda-registered" data-testid="registered-badge">
                  You&apos;re registered
                </span>
              )}
            </div>
          )}
          {canWrite && (
            <div className="agenda-roster" data-testid="roster">
              <h4>Participants ({roster.length})</h4>
              {roster.length === 0 ? (
                <p data-testid="roster-empty">No one has registered yet.</p>
              ) : (
                <ul className="roster-list">
                  {roster.map((p) => (
                    <li key={p.user_id}>{p.full_name || p.email} — {p.email}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {agendaItems.length === 0 ? (
            <p data-testid="agenda-empty">
              No sessions yet for this event.
              {canWrite ? " Add talks to build the agenda." : " Check back soon."}
            </p>
          ) : (
            <>
              <ul className="session-modes" data-testid="session-modes">
                {selected.sessions.map((s) => (
                  <li key={s.id} className="session-mode-row">
                    <span className="session-mode-title">{s.title}</span>
                    <span className={`session-mode-chip mode-${s.mode}`}>
                      {MODE_LABEL[s.mode]}
                    </span>
                    {s.stream_url && (
                      <a
                        className="session-link"
                        href={s.stream_url}
                        target="_blank"
                        rel="noreferrer"
                        data-testid={`stream-${s.id}`}
                      >
                        Live stream
                      </a>
                    )}
                    {s.recording_url && (
                      <a
                        className="session-link"
                        href={s.recording_url}
                        target="_blank"
                        rel="noreferrer"
                        data-testid={`recording-${s.id}`}
                      >
                        ▶ Recording
                      </a>
                    )}
                  </li>
                ))}
              </ul>
              <Scheduler data={agendaItems} defaultDate={new Date(selected.starts_at)}>
                <DayView />
                <WeekView />
              </Scheduler>
            </>
          )}

          {/* Hackathon workspace (S7.3) — only for hackathon-typed events. */}
          {selected.event_type === "hackathon" && (
            <HackathonPanel eventId={selected.id} fetchImpl={fetchImpl} />
          )}

          {/* Webinar workspace (S7.4) — only for webinar-typed events. */}
          {selected.event_type === "webinar" && (
            <WebinarPanel eventId={selected.id} fetchImpl={fetchImpl} />
          )}

          {/* Linked / hybrid events (S7.5) — available for every event type. */}
          <LinkedEventsPanel
            eventId={selected.id}
            linkableEvents={events.map((e) => ({ id: e.id, name: e.name }))}
            canManage={canWrite}
            fetchImpl={fetchImpl}
          />

          {/* Type-aware AI plan draft (S7.6) — available for every event type. */}
          <PlanPanel
            eventId={selected.id}
            eventType={selected.event_type}
            fetchImpl={fetchImpl}
          />

          {/* On-demand recordings catalog (S7.2). */}
          {recordings.length > 0 && (
            <div className="recordings" data-testid="recordings">
              <h4>Recordings ({recordings.length})</h4>
              <ul className="recordings-list">
                {recordings.map((r) => (
                  <li key={r.id}>
                    <a
                      href={r.recording_url}
                      target="_blank"
                      rel="noreferrer"
                      data-testid={`catalog-${r.id}`}
                    >
                      ▶ {r.title}
                    </a>{" "}
                    — {r.speaker || "TBA"}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {showForm && (
        <Dialog title="New event" onClose={() => setShowForm(false)}>
          <EventForm
            submitLabel="Create"
            initial={{ ...defaultWindow(), ...newEventDefaults }}
            onSubmit={handleCreate}
            onCancel={() => setShowForm(false)}
          />
        </Dialog>
      )}
    </section>
  );
}
