import { useCallback, useEffect, useState } from "react";
import { Button } from "@progress/kendo-react-buttons";
import {
  webinarStatus,
  webinarRegister,
  webinarCancel,
  webinarReminders,
  type WebinarStatus,
  type Reminder,
} from "../lib/webinar";

interface Props {
  eventId: string;
  fetchImpl?: typeof fetch;
}

/**
 * Webinar workspace shown when an event's type is "webinar" (S7.4):
 * a live seat counter, join/leave (with waitlist overflow + position), the
 * stream link once registered, and the reminder schedule.
 */
export function WebinarPanel({ eventId, fetchImpl = fetch }: Props) {
  const [status, setStatus] = useState<WebinarStatus | null>(null);
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const [s, r] = await Promise.all([
        webinarStatus(eventId, fetchImpl),
        webinarReminders(eventId, fetchImpl),
      ]);
      setStatus(s);
      setReminders(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load webinar data");
    }
  }, [eventId, fetchImpl]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleJoin = async () => {
    setBusy(true);
    setError(null);
    try {
      await webinarRegister(eventId, fetchImpl);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not register");
    } finally {
      setBusy(false);
    }
  };

  const handleLeave = async () => {
    setBusy(true);
    setError(null);
    try {
      await webinarCancel(eventId, fetchImpl);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not cancel");
    } finally {
      setBusy(false);
    }
  };

  if (status === null) {
    return (
      <section className="webinar" data-testid="webinar-panel">
        <h3>Webinar</h3>
        {error ? (
          <p role="alert" data-testid="webinar-error" className="webinar-error">
            {error}
          </p>
        ) : (
          <p data-testid="webinar-loading">Loading…</p>
        )}
      </section>
    );
  }

  const isRegistered = status.my_state === "registered";
  const isWaitlisted = status.my_state === "waitlisted";
  const isActive = isRegistered || isWaitlisted;
  const seatLabel =
    status.seats_left === null
      ? "Unlimited seats"
      : `${status.seats_left} of ${status.capacity} seats left`;

  return (
    <section className="webinar" data-testid="webinar-panel">
      <h3>Webinar</h3>

      {error && (
        <p role="alert" data-testid="webinar-error" className="webinar-error">
          {error}
        </p>
      )}

      <div className="webinar-status" data-testid="webinar-seats">
        <span className="webinar-seat-count">{seatLabel}</span>
        <span className="webinar-counts">
          {status.registered_count} registered · {status.waitlisted_count} waitlisted
        </span>
      </div>

      {isWaitlisted && (
        <p className="webinar-waitlisted" data-testid="webinar-waitlisted">
          You're on the waitlist — we'll promote you automatically if a seat frees up.
        </p>
      )}

      {isRegistered && status.stream_url && (
        <p className="webinar-stream">
          <a
            href={status.stream_url}
            target="_blank"
            rel="noreferrer"
            data-testid="webinar-stream-link"
          >
            Join the live stream
          </a>
        </p>
      )}

      <div className="webinar-actions">
        {isActive ? (
          <Button onClick={() => void handleLeave()} disabled={busy} data-testid="webinar-leave">
            {isWaitlisted ? "Leave waitlist" : "Cancel registration"}
          </Button>
        ) : (
          <Button
            themeColor="primary"
            onClick={() => void handleJoin()}
            disabled={busy}
            data-testid="webinar-join"
          >
            {status.seats_left === 0 ? "Join waitlist" : "Register"}
          </Button>
        )}
      </div>

      <div className="webinar-reminders" data-testid="webinar-reminders">
        <h4>Reminders</h4>
        {reminders.length === 0 ? (
          <p data-testid="reminders-empty">No reminders scheduled.</p>
        ) : (
          <ul>
            {reminders.map((r) => (
              <li key={r.offset} data-testid={`reminder-${r.offset}`}>
                {r.offset} before · {new Date(r.send_at).toLocaleString()}
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
