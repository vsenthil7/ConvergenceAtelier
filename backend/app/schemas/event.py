"""Request/response schemas for events and agenda sessions.

All datetimes are timezone-aware; naive inputs are rejected so the database never
receives a naive datetime (pre-mitigation for the naive/aware subtraction bug).
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _require_aware(value: datetime, field: str) -> datetime:
    if value.tzinfo is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value


class SessionBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    track: str = Field(default="General", max_length=100)
    speaker: str = Field(default="", max_length=200)
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def _check(self) -> "SessionBase":
        _require_aware(self.starts_at, "starts_at")
        _require_aware(self.ends_at, "ends_at")
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class SessionCreate(SessionBase):
    pass


class SessionRead(SessionBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    event_id: str


class EventBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    location: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=5000)
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def _check(self) -> "EventBase":
        _require_aware(self.starts_at, "starts_at")
        _require_aware(self.ends_at, "ends_at")
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    """Partial update; only provided fields change."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
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


class EventRead(EventBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    sessions: list[SessionRead] = []
