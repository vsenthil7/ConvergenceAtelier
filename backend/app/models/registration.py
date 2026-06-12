"""Event registration: links a User to an Event they intend to attend (S3b).

A registration is the participation layer the platform previously lacked: users
belong to a tenant, but attendance is per-event. Each (event, user) pair is
unique. Status allows a simple lifecycle (registered → cancelled) without losing
the row, and is tz-aware throughout.
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.event import Event
from app.models.identity import User


def _uuid() -> str:
    return uuid.uuid4().hex


class RegistrationStatus(str, enum.Enum):
    REGISTERED = "registered"
    CANCELLED = "cancelled"
    # Webinar capacity overflow (S7.4): seat filled → placed on the waitlist,
    # auto-promoted to REGISTERED when a seat frees up.
    WAITLISTED = "waitlisted"


class EventRegistration(TimestampMixin, Base):
    """A person's registration for a specific event."""

    __tablename__ = "event_registrations"
    __table_args__ = (
        UniqueConstraint("event_id", "user_id", name="uq_event_user"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    event_id: Mapped[str] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[RegistrationStatus] = mapped_column(
        Enum(RegistrationStatus),
        default=RegistrationStatus.REGISTERED,
        nullable=False,
    )

    event: Mapped[Event] = relationship()
    user: Mapped[User] = relationship()
