"""Schemas for the event-links module (S7.5)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.event import EventType


class LinkRequest(BaseModel):
    other_event_id: str


class LinkedEventRead(BaseModel):
    id: str
    name: str
    location: str
    event_type: EventType
    starts_at: datetime
    ends_at: datetime


class CatalogSessionRead(BaseModel):
    session_id: str
    event_id: str
    event_name: str
    title: str
    track: str
    speaker: str
    mode: str
    stream_url: str
    recording_url: str
    starts_at: datetime
