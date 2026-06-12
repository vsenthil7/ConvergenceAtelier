import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { PlanPanel } from "../components/PlanPanel";

const hackPlan = [
  { order: 0, key: "registration", label: "Open registration", detail: "x", target_at: "2026-07-01T09:00:00+00:00", relevance: 0.12 },
  { order: 1, key: "judging", label: "Judging & scoring", detail: "y", target_at: "2026-07-03T09:00:00+00:00", relevance: 0.81 },
];

function makeFetch(rows: unknown = hackPlan, ok = true, status = 200): typeof fetch {
  return vi.fn(async () => ({ ok, status, json: async () => rows })) as unknown as typeof fetch;
}

describe("PlanPanel", () => {
  it("labels the draft button by event type (functional)", () => {
    render(<PlanPanel eventId="e1" eventType="hackathon" fetchImpl={makeFetch()} />);
    expect(screen.getByTestId("plan-draft")).toHaveTextContent("Draft a judging schedule");
  });

  it("labels webinar as a promo timeline (functional)", () => {
    render(<PlanPanel eventId="e1" eventType="webinar" fetchImpl={makeFetch()} />);
    expect(screen.getByTestId("plan-draft")).toHaveTextContent("Draft a promo timeline");
  });

  it("drafts a plan and lists the milestones (functional)", async () => {
    render(<PlanPanel eventId="e1" eventType="hackathon" fetchImpl={makeFetch()} />);
    await userEvent.click(screen.getByTestId("plan-draft"));
    const list = await screen.findByTestId("plan-list");
    expect(within(list).getByTestId("plan-registration")).toBeInTheDocument();
    expect(within(list).getByTestId("plan-judging")).toBeInTheDocument();
  });

  it("shows relevance only when a theme was entered (functional)", async () => {
    render(<PlanPanel eventId="e1" eventType="hackathon" fetchImpl={makeFetch()} />);
    await userEvent.type(screen.getByLabelText("plan-theme"), "judging");
    await userEvent.click(screen.getByTestId("plan-draft"));
    await screen.findByTestId("plan-list");
    expect(screen.getByTestId("relevance-judging")).toHaveTextContent("81% match");
  });

  it("hides relevance when no theme is given (functional)", async () => {
    render(<PlanPanel eventId="e1" eventType="hackathon" fetchImpl={makeFetch()} />);
    await userEvent.click(screen.getByTestId("plan-draft"));
    await screen.findByTestId("plan-list");
    expect(screen.queryByTestId("relevance-judging")).not.toBeInTheDocument();
  });

  it("shows an empty message when the plan has no items (negative)", async () => {
    render(<PlanPanel eventId="e1" eventType="conference" fetchImpl={makeFetch([])} />);
    await userEvent.click(screen.getByTestId("plan-draft"));
    expect(await screen.findByTestId("plan-empty")).toBeInTheDocument();
  });

  it("falls back to a generic label for an unknown type (edge)", () => {
    render(<PlanPanel eventId="e1" eventType="mystery" fetchImpl={makeFetch()} />);
    expect(screen.getByTestId("plan-draft")).toHaveTextContent("Draft a plan");
  });

  it("surfaces an error when drafting fails (negative)", async () => {
    const f = makeFetch({ detail: "Event not found" }, false, 404);
    render(<PlanPanel eventId="e1" eventType="hackathon" fetchImpl={f} />);
    await userEvent.click(screen.getByTestId("plan-draft"));
    expect(await screen.findByTestId("plan-error")).toHaveTextContent("Event not found");
  });

  it("uses a fallback message when drafting rejects with a non-Error (negative)", async () => {
    const f = vi.fn(async () => {
      throw "boom";
    }) as unknown as typeof fetch;
    render(<PlanPanel eventId="e1" eventType="hackathon" fetchImpl={f} />);
    await userEvent.click(screen.getByTestId("plan-draft"));
    expect(await screen.findByTestId("plan-error")).toHaveTextContent("Could not draft a plan");
  });
});
