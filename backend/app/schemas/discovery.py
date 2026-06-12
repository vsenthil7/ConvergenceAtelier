"""Request/response schemas for AI discovery (S3).

Responses reuse ``SessionRead`` so the agenda shape stays consistent across the
API, wrapping each with a 0..1 ``score``.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.event import SessionRead


class ScoredSessionRead(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    session: SessionRead


class InterestQuery(BaseModel):
    interests: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=50)


class AttendeeProfileIn(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    name: str = Field(default="", max_length=200)
    interests: str = Field(default="", max_length=2000)


class MatchRequest(BaseModel):
    attendees: list[AttendeeProfileIn] = Field(min_length=2)
    limit: int = Field(default=5, ge=1, le=100)


class AttendeeRef(BaseModel):
    id: str
    name: str


class AttendeeMatchRead(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    a: AttendeeRef
    b: AttendeeRef


class AgendaDraftRequest(BaseModel):
    theme: str = Field(min_length=1, max_length=500)


class AgendaSlotRead(BaseModel):
    order: int
    relevance: float = Field(ge=0.0, le=1.0)
    track: str
    session: SessionRead
