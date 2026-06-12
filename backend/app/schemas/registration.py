"""Schemas for event registration + participation (S3b)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.models.registration import RegistrationStatus


class RegistrationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    event_id: str
    user_id: str
    status: RegistrationStatus


class MyRegistrationStatus(BaseModel):
    """The caller's own status for an event (status None = never registered)."""

    event_id: str
    status: RegistrationStatus | None


class ParticipantRead(BaseModel):
    user_id: str
    email: str
    full_name: str
    status: RegistrationStatus
