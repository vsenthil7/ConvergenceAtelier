import { useState } from "react";
import { Button } from "@progress/kendo-react-buttons";
import { Input } from "@progress/kendo-react-inputs";
import { draftPlan, type PlanItem } from "../lib/plan";

interface Props {
  eventId: string;
  eventType: string;
  fetchImpl?: typeof fetch;
}

const PLAN_LABEL: Record<string, string> = {
  hackathon: "judging schedule",
  webinar: "promo timeline",
  workshop: "workshop plan",
  conference: "run-of-show",
  meetup: "run-of-show",
  hybrid: "run-of-show",
};

/**
 * Type-aware AI plan draft (S7.6). One button drafts the plan the event type
 * actually needs — a hackathon a judging schedule, a webinar a promo timeline,
 * etc. Each milestone shows its target time and theme relevance.
 */
export function PlanPanel({ eventId, eventType, fetchImpl = fetch }: Props) {
  const [theme, setTheme] = useState("");
  const [plan, setPlan] = useState<PlanItem[]>([]);
  const [drafted, setDrafted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const planKind = PLAN_LABEL[eventType] ?? "plan";

  const handleDraft = async () => {
    setBusy(true);
    setError(null);
    try {
      const items = await draftPlan(eventId, theme, fetchImpl);
      setPlan(items);
      setDrafted(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not draft a plan");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="plan-panel" data-testid="plan-panel">
      <h3>AI plan draft</h3>
      <p className="plan-hint">
        Draft a {planKind} tailored to this {eventType} — optionally focused on a theme.
      </p>

      {error && (
        <p role="alert" data-testid="plan-error" className="plan-error">
          {error}
        </p>
      )}

      <div className="plan-controls">
        <Input
          aria-label="plan-theme"
          placeholder="Optional focus (e.g. accessibility)"
          value={theme}
          onChange={(e) => setTheme(String(e.value ?? ""))}
        />
        <Button
          themeColor="primary"
          onClick={() => void handleDraft()}
          disabled={busy}
          data-testid="plan-draft"
        >
          Draft a {planKind}
        </Button>
      </div>

      {drafted &&
        (plan.length === 0 ? (
          <p data-testid="plan-empty">No plan items for this event.</p>
        ) : (
          <ol className="plan-list" data-testid="plan-list">
            {plan.map((item) => (
              <li key={item.key} data-testid={`plan-${item.key}`}>
                <span className="plan-label">{item.label}</span>
                <span className="plan-time">
                  {new Date(item.target_at).toLocaleDateString()}
                </span>
                {theme && (
                  <span className="plan-relevance" data-testid={`relevance-${item.key}`}>
                    {Math.round(item.relevance * 100)}% match
                  </span>
                )}
              </li>
            ))}
          </ol>
        ))}
    </section>
  );
}
