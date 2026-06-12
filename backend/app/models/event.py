"""Event + agenda Session models (timezone-aware throughout).

Events are tenant-scoped: every event belongs to exactly one tenant, and the
service layer filters by the caller's tenant (super-admins may span all).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AwareDateTime, Base, TimestampMixin


def _uuid() -> str:
    return uuid.uuid4().hex


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
    starts_at: Mapped[datetime] = mapped_column(AwareDateTime, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(AwareDateTime, nullable=False)

    event: Mapped[Event] = relationship(back_populates="sessions")
