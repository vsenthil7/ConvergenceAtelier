"""Schemas for the webinar module (S7.4)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.registration import RegistrationStatus


class WebinarStatusRead(BaseModel):
    event_id: str
    capacity: int  # 0 = unlimited
    registered_count: int
    waitlisted_count: int
    seats_left: int | None
    my_state: RegistrationStatus | None
    stream_url: str


class WaitlistEntryRead(BaseModel):
    user_id: str
    email: str
    full_name: str
    position: int


class ReminderRead(BaseModel):
    offset: str
    send_at: datetime


class WebinarRegistrationRead(BaseModel):
    event_id: str
    status: RegistrationStatus
