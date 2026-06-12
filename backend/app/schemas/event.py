"""Request/response schemas for events and agenda sessions.

Inbound datetimes must be timezone-aware (naive inputs are rejected). On the way
out, datetimes loaded from SQLite come back naive (SQLite drops tzinfo), so the
read schemas coerce them back to UTC-aware rather than rejecting them.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.event import EventType, SessionMode


def _require_aware(value: datetime, field: str) -> datetime:
    if value.tzinfo is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value


def _as_utc(value: datetime) -> datetime:
    """Coerce a possibly-naive datetime to UTC-aware (storage is always UTC)."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


# ---------- inbound (write) ----------

class SessionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    track: str = Field(default="General", max_length=100)
    speaker: str = Field(default="", max_length=200)
    mode: SessionMode = SessionMode.IN_PERSON
    stream_url: str = Field(default="", max_length=500)
    meeting_url: str = Field(default="", max_length=500)
    recording_url: str = Field(default="", max_length=500)
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def _check(self) -> "SessionCreate":
        _require_aware(self.starts_at, "starts_at")
        _require_aware(self.ends_at, "ends_at")
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class EventCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    location: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=5000)
    event_type: EventType = EventType.CONFERENCE
    config: dict[str, Any] = Field(default_factory=dict)
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def _check(self) -> "EventCreate":
        _require_aware(self.starts_at, "starts_at")
        _require_aware(self.ends_at, "ends_at")
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class EventUpdate(BaseModel):
    """Partial update; only provided fields change."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    event_type: EventType | None = None
    config: dict[str, Any] | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None

    @model_validator(mode="after")
    def _check(self) -> "EventUpdate":
        if self.starts_at is not None:
            _require_aware(self.starts_at, "starts_at")
        if self.ends_at is not None:
            _require_aware(self.ends_at, "ends_at")
        if (
            self.starts_at is not None
            and self.ends_at is not None
            and self.ends_at <= self.starts_at
        ):
            raise ValueError("ends_at must be after starts_at")
        return self


# ---------- outbound (read) ----------

class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    event_id: str
    title: str
    track: str
    speaker: str
    mode: SessionMode
    stream_url: str = ""
    meeting_url: str = ""
    recording_url: str = ""
    starts_at: datetime
    ends_at: datetime

    @field_validator("starts_at", "ends_at", mode="after")
    @classmethod
    def _coerce(cls, v: datetime) -> datetime:
        return _as_utc(v)


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    location: str
    description: str
    event_type: EventType
    config: dict[str, Any] = {}
    starts_at: datetime
    ends_at: datetime
    sessions: list[SessionRead] = []

    @field_validator("starts_at", "ends_at", mode="after")
    @classmethod
    def _coerce(cls, v: datetime) -> datetime:
        return _as_utc(v)
