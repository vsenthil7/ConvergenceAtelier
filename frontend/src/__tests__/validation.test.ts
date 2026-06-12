import { describe, it, expect } from "vitest";
import { validateEvent } from "../lib/validation";

const base = {
  name: "React Summit",
  location: "Amsterdam",
  description: "",
  starts_at: "2026-06-11T09:00:00+00:00",
  ends_at: "2026-06-12T17:00:00+00:00",
};

describe("validateEvent", () => {
  it("accepts a valid event (functional)", () => {
    expect(validateEvent(base).valid).toBe(true);
  });

  it("rejects a blank name (negative)", () => {
    const r = validateEvent({ ...base, name: "   " });
    expect(r.valid).toBe(false);
    expect(r.errors.name).toBeDefined();
  });

  it("rejects an over-long name (negative)", () => {
    const r = validateEvent({ ...base, name: "x".repeat(201) });
    expect(r.errors.name).toContain("200");
  });

  it("rejects a missing start (negative)", () => {
    const r = validateEvent({ ...base, starts_at: "" });
    expect(r.errors.starts_at).toBeDefined();
  });

  it("rejects a missing end (negative)", () => {
    const r = validateEvent({ ...base, ends_at: "" });
    expect(r.errors.ends_at).toBeDefined();
  });

  it("rejects end before start (negative)", () => {
    const r = validateEvent({
      ...base,
      starts_at: "2026-06-12T17:00:00+00:00",
      ends_at: "2026-06-11T09:00:00+00:00",
    });
    expect(r.errors.ends_at).toContain("after");
  });
});
