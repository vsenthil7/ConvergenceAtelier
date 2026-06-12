import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { DiscoveryView } from "../components/DiscoveryView";

function sessionRow(id: string, title: string, score: number, speaker = "Ada") {
  return {
    score,
    session: {
      id,
      event_id: "e1",
      title,
      track: "Frontend",
      speaker,
      starts_at: "2026-06-11T10:00:00.000Z",
      ends_at: "2026-06-11T11:00:00.000Z",
    },
  };
}

function recommendFetch(rows: unknown[], fails = false): typeof fetch {
  return vi.fn(async () => {
    if (fails) return { ok: false, status: 500, json: async () => ({ detail: "boom" }) };
    return { ok: true, status: 200, json: async () => rows };
  }) as unknown as typeof fetch;
}

describe("DiscoveryView", () => {
  it("disables Recommend until interests are entered (functional)", async () => {
    render(<DiscoveryView fetchImpl={recommendFetch([])} />);
    const btn = screen.getByTestId("discovery-search");
    expect(btn).toBeDisabled();
    await userEvent.type(screen.getByLabelText("discovery-interests"), "react");
    expect(btn).not.toBeDisabled();
  });

  it("shows ranked results with score badges (functional)", async () => {
    const f = recommendFetch([
      sessionRow("s1", "React hooks deep dive", 0.92),
      sessionRow("s2", "Sourdough baking", 0.10, ""),
    ]);
    render(<DiscoveryView fetchImpl={f} />);
    await userEvent.type(screen.getByLabelText("discovery-interests"), "react");
    await userEvent.click(screen.getByTestId("discovery-search"));
    expect(await screen.findByTestId("discovery-results")).toBeInTheDocument();
    expect(screen.getByText("React hooks deep dive")).toBeInTheDocument();
    // 0.92 -> 92%
    expect(screen.getByLabelText("match-92")).toBeInTheDocument();
    // empty speaker -> TBA fallback
    expect(screen.getByText("TBA")).toBeInTheDocument();
  });

  it("shows an empty state when no sessions come back (functional)", async () => {
    render(<DiscoveryView fetchImpl={recommendFetch([])} />);
    await userEvent.type(screen.getByLabelText("discovery-interests"), "obscure topic");
    await userEvent.click(screen.getByTestId("discovery-search"));
    expect(await screen.findByTestId("discovery-empty")).toBeInTheDocument();
  });

  it("surfaces an error when the API fails (negative)", async () => {
    render(<DiscoveryView fetchImpl={recommendFetch([], true)} />);
    await userEvent.type(screen.getByLabelText("discovery-interests"), "react");
    await userEvent.click(screen.getByTestId("discovery-search"));
    expect(await screen.findByTestId("discovery-error")).toHaveTextContent("boom");
  });
});
