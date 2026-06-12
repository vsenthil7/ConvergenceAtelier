import { useCallback, useEffect, useState } from "react";
import { Button } from "@progress/kendo-react-buttons";
import {
  listLinks,
  linkEvent,
  unlinkEvent,
  combinedCatalog,
  type LinkedEvent,
  type CatalogSession,
} from "../lib/links";

interface Props {
  eventId: string;
  /** Other events the admin can link to (same tenant, excluding this one). */
  linkableEvents?: { id: string; name: string }[];
  canManage?: boolean;
  fetchImpl?: typeof fetch;
}

/**
 * Linked-events panel (S7.5): shows the events linked into this series, lets an
 * admin link/unlink others, and renders a combined "Across this series" session
 * catalog spanning the event and everything linked to it.
 */
export function LinkedEventsPanel({
  eventId,
  linkableEvents = [],
  canManage = false,
  fetchImpl = fetch,
}: Props) {
  const [links, setLinks] = useState<LinkedEvent[]>([]);
  const [catalog, setCatalog] = useState<CatalogSession[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [pick, setPick] = useState("");

  const refresh = useCallback(async () => {
    try {
      const [l, c] = await Promise.all([
        listLinks(eventId, fetchImpl),
        combinedCatalog(eventId, fetchImpl),
      ]);
      setLinks(l);
      setCatalog(c);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load linked events");
    }
  }, [eventId, fetchImpl]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleLink = async () => {
    setBusy(true);
    setError(null);
    try {
      await linkEvent(eventId, pick, fetchImpl);
      setPick("");
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not link event");
    } finally {
      setBusy(false);
    }
  };

  const handleUnlink = async (otherId: string) => {
    setBusy(true);
    setError(null);
    try {
      await unlinkEvent(eventId, otherId, fetchImpl);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not unlink event");
    } finally {
      setBusy(false);
    }
  };

  const linkedIds = new Set(links.map((l) => l.id));
  const available = linkableEvents.filter((e) => e.id !== eventId && !linkedIds.has(e.id));

  return (
    <section className="linked-events" data-testid="linked-panel">
      <h3>Linked events</h3>

      {error && (
        <p role="alert" data-testid="linked-error" className="linked-error">
          {error}
        </p>
      )}

      {links.length === 0 ? (
        <p data-testid="links-empty">This event isn't linked to any others yet.</p>
      ) : (
        <ul className="linked-list" data-testid="linked-list">
          {links.map((l) => (
            <li key={l.id}>
              <span className="linked-name">{l.name}</span>{" "}
              <span className={`event-type-badge event-type-${l.event_type}`}>
                {l.event_type}
              </span>{" "}
              {canManage && (
                <Button
                  fillMode="flat"
                  onClick={() => void handleUnlink(l.id)}
                  disabled={busy}
                  data-testid={`unlink-${l.id}`}
                >
                  Unlink
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}

      {canManage && available.length > 0 && (
        <div className="linked-add" data-testid="linked-add">
          <select
            aria-label="link-target"
            value={pick}
            onChange={(e) => setPick(e.target.value)}
            className="k-input k-input-md k-rounded-md k-input-solid"
          >
            <option value="">Link another event…</option>
            {available.map((e) => (
              <option key={e.id} value={e.id}>
                {e.name}
              </option>
            ))}
          </select>
          <Button
            themeColor="primary"
            onClick={() => void handleLink()}
            disabled={busy || !pick}
            data-testid="link-button"
          >
            Link
          </Button>
        </div>
      )}

      <div className="series-catalog" data-testid="series-catalog">
        <h4>Across this series ({catalog.length})</h4>
        {catalog.length === 0 ? (
          <p data-testid="catalog-empty">No sessions in this series yet.</p>
        ) : (
          <ul className="series-list">
            {catalog.map((s) => (
              <li key={s.session_id} data-testid={`series-${s.session_id}`}>
                <span className="series-title">{s.title}</span>{" "}
                <span className="series-source">— {s.event_name}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
