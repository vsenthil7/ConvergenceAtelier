// Client-side validation mirroring the backend schema rules, so the Form gives
// immediate feedback and we never send a request the API would 422.

import type { EventInput } from "./events";

export interface ValidationResult {
  valid: boolean;
  errors: Partial<Record<keyof EventInput, string>>;
}

export function validateEvent(input: EventInput): ValidationResult {
  const errors: Partial<Record<keyof EventInput, string>> = {};

  if (!input.name || input.name.trim().length === 0) {
    errors.name = "Name is required";
  } else if (input.name.length > 200) {
    errors.name = "Name must be 200 characters or fewer";
  }

  const start = Date.parse(input.starts_at);
  const end = Date.parse(input.ends_at);

  if (Number.isNaN(start)) {
    errors.starts_at = "Start date/time is required";
  }
  if (Number.isNaN(end)) {
    errors.ends_at = "End date/time is required";
  }
  if (!Number.isNaN(start) && !Number.isNaN(end) && end <= start) {
    errors.ends_at = "End must be after start";
  }

  return { valid: Object.keys(errors).length === 0, errors };
}
