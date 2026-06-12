"""Event + agenda Session models (timezone-aware throughout).

Events are tenant-scoped: every event belongs to exactly one tenant, and the
service layer filters by the caller's tenant (super-admins may span all).

Events are *typed* (S7): an ``event_type`` selects which feature modules apply,
and a free-form ``config`` JSON object carries type-specific settings without
schema churn. The agenda/session/registration layers are shared by every type.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Enum, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AwareDateTime, Base, TimestampMixin


def _uuid() -> str:
    return uuid.uuid4().hex


class EventType(str, enum.Enum):
    """The shape of an event; selects which feature modules apply (S7).

    CONFERENCE — multi-track agenda, speakers, rooms (the default, always valid).
    HACKATHON  — teams, project submissions, judging, leaderboard.
    WEBINAR    — single stream, capacity cap, recording, reminders.
    MEETUP     — RSVP, venue, casual / recurring.
    WORKSHOP   — limited seats, materials, prerequisites.
    HYBRID     — links physical + online events, shared catalog.
    """

    CONFERENCE = "conference"
    HACKATHON = "hackathon"
    WEBINAR = "webinar"
    MEETUP = "meetup"
    WORKSHOP = "workshop"
    HYBRID = "hybrid"


class SessionMode(str, enum.Enum):
    """How a session is delivered (S7.2).

    IN_PERSON — on-site only (the default for conferences).
    ONLINE    — streamed / remote only (webinars, online tracks).
    HYBRID    — both on-site and streamed.
    """

    IN_PERSON = "in_person"
    ONLINE = "online"
    HYBRID = "hybrid"


class Event(TimestampMixin, Base):
    """A conference/event the organiser is running (tenant-scoped)."""

    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType), default=EventType.CONFERENCE, nullable=False
    )
    # Type-specific settings (e.g. webinar stream URL, hackathon judging window).
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(AwareDateTime, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(AwareDateTime, nullable=False)

    sessions: Mapped[list["Session"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
        order_by="Session.starts_at",
    )


class Session(TimestampMixin, Base):
    """An agenda item / talk within an event."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    event_id: Mapped[str] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    track: Mapped[str] = mapped_column(String(100), default="General", nullable=False)
    speaker: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    mode: Mapped[SessionMode] = mapped_column(
        Enum(SessionMode), default=SessionMode.IN_PERSON, nullable=False
    )
    # Live stream URL (online/hybrid), interactive meeting link, and the
    # on-demand recording URL published after the talk. Empty when not set.
    stream_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    meeting_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    recording_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    starts_at: Mapped[datetime] = mapped_column(AwareDateTime, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(AwareDateTime, nullable=False)

    event: Mapped[Event] = relationship(back_populates="sessions")
