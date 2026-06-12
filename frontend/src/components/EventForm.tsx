import { useState } from "react";
import { Input, TextArea } from "@progress/kendo-react-inputs";
import { DateTimePicker } from "@progress/kendo-react-dateinputs";
import { Button } from "@progress/kendo-react-buttons";
import type { EventInput } from "../lib/events";
import { validateEvent } from "../lib/validation";

interface Props {
  initial?: Partial<EventInput>;
  submitLabel?: string;
  onSubmit: (input: EventInput) => void | Promise<void>;
  onCancel?: () => void;
}

const EMPTY: EventInput = {
  name: "",
  location: "",
  description: "",
  starts_at: "",
  ends_at: "",
};

export function EventForm({ initial, submitLabel = "Save", onSubmit, onCancel }: Props) {
  const [form, setForm] = useState<EventInput>({ ...EMPTY, ...initial });
  const [errors, setErrors] = useState<ReturnType<typeof validateEvent>["errors"]>({});
  const [submitting, setSubmitting] = useState(false);

  const set = (field: keyof EventInput, value: string) =>
    setForm((f) => ({ ...f, [field]: value }));

  const handleSubmit = async () => {
    const result = validateEvent(form);
    setErrors(result.errors);
    if (!result.valid) return;
    setSubmitting(true);
    try {
      await onSubmit(form);
    } finally {
      setSubmitting(false);
    }
  };

  const asDate = (v: string): Date | null => {
    const t = Date.parse(v);
    return Number.isNaN(t) ? null : new Date(t);
  };

  return (
    <div className="event-form">
      <label>
        Name
        <Input
          value={form.name}
          onChange={(e) => set("name", String(e.value ?? ""))}
          aria-label="event-name"
        />
      </label>
      {errors.name && (
        <span role="alert" data-testid="err-name">
          {errors.name}
        </span>
      )}

      <label>
        Location
        <Input
          value={form.location}
          onChange={(e) => set("location", String(e.value ?? ""))}
          aria-label="event-location"
        />
      </label>

      <label>
        Description
        <TextArea
          value={form.description}
          onChange={(e) => set("description", String(e.value ?? ""))}
          aria-label="event-description"
        />
      </label>

      <label>
        Starts
        <DateTimePicker
          value={asDate(form.starts_at)}
          onChange={(e) => set("starts_at", e.value ? e.value.toISOString() : "")}
          aria-label="event-starts"
        />
      </label>

      <label>
        Ends
        <DateTimePicker
          value={asDate(form.ends_at)}
          onChange={(e) => set("ends_at", e.value ? e.value.toISOString() : "")}
          aria-label="event-ends"
        />
      </label>
      {errors.ends_at && (
        <span role="alert" data-testid="err-ends">
          {errors.ends_at}
        </span>
      )}

      <div className="event-form-actions">
        <Button themeColor="primary" onClick={() => void handleSubmit()} disabled={submitting}>
          {submitLabel}
        </Button>
        {onCancel && (
          <Button onClick={onCancel} disabled={submitting}>
            Cancel
          </Button>
        )}
      </div>
    </div>
  );
}
