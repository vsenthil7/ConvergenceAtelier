import { useCallback, useEffect, useState } from "react";
import { Grid, GridColumn, type GridCellProps } from "@progress/kendo-react-grid";
import { Scheduler, DayView, WeekView } from "@progress/kendo-react-scheduler";
import { Dialog } from "@progress/kendo-react-dialogs";
import { Button } from "@progress/kendo-react-buttons";
import { Loader } from "@progress/kendo-react-indicators";
import {
  listEvents,
  createEvent,
  deleteEvent,
  type EventModel,
  type EventInput,
} from "../lib/events";
import { EventForm } from "./EventForm";

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

  const ActionsCell = (props: GridCellProps) => {
    const row = props.dataItem as EventModel;
    return (
      <td>
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
            <GridColumn field="location" title="Location" />
            <GridColumn field="starts_at" title="Starts" />
            <GridColumn field="ends_at" title="Ends" />
            <GridColumn title="Actions" cell={ActionsCell} />
          </Grid>
        </div>
      )}

      {selected && (
        <div className="agenda" data-testid="agenda">
          <h3>Agenda — {selected.name}</h3>
          <Scheduler data={agendaItems} defaultDate={new Date(selected.starts_at)}>
            <DayView />
            <WeekView />
          </Scheduler>
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
