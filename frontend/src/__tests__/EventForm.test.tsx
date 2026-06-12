import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { EventForm } from "../components/EventForm";
import type { EventInput } from "../lib/events";

const valid: EventInput = {
  name: "React Summit",
  location: "Amsterdam",
  description: "JS conf",
  starts_at: "2026-06-11T09:00:00.000Z",
  ends_at: "2026-06-12T17:00:00.000Z",
};

describe("EventForm", () => {
  it("submits when valid (functional)", async () => {
    const onSubmit = vi.fn();
    render(<EventForm initial={valid} onSubmit={onSubmit} />);
    await userEvent.click(screen.getByText("Save"));
    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith(valid));
  });

  it("blocks submit and shows error when name is blank (negative)", async () => {
    const onSubmit = vi.fn();
    render(<EventForm initial={{ ...valid, name: "" }} onSubmit={onSubmit} />);
    await userEvent.click(screen.getByText("Save"));
    expect(await screen.findByTestId("err-name")).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("blocks submit and shows error when end is before start (negative)", async () => {
    const onSubmit = vi.fn();
    render(
      <EventForm
        initial={{ ...valid, starts_at: valid.ends_at, ends_at: valid.starts_at }}
        onSubmit={onSubmit}
      />,
    );
    await userEvent.click(screen.getByText("Save"));
    expect(await screen.findByTestId("err-ends")).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("edits the name field (functional)", async () => {
    const onSubmit = vi.fn();
    render(<EventForm initial={valid} onSubmit={onSubmit} />);
    const input = screen.getByLabelText("event-name");
    await userEvent.clear(input);
    await userEvent.type(input, "JSNation");
    await userEvent.click(screen.getByText("Save"));
    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ name: "JSNation" })),
    );
  });

  it("invokes onCancel (functional)", async () => {
    const onCancel = vi.fn();
    render(<EventForm initial={valid} onSubmit={vi.fn()} onCancel={onCancel} />);
    await userEvent.click(screen.getByText("Cancel"));
    expect(onCancel).toHaveBeenCalled();
  });
});
