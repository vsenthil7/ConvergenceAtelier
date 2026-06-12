"""Event-to-event links (S7.5): connect related events into a series.

A link is *symmetric* and *unordered* — linking A↔B is the same as B↔A. To keep
the pair unique regardless of direction, the two ids are stored in a canonical
order (the lexicographically smaller id in ``event_a_id``). Both events must
belong to the same tenant; the service enforces that.
"""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.event import Event


def _uuid() -> str:
    return uuid.uuid4().hex


class EventLink(TimestampMixin, Base):
    """A symmetric association between two events in the same series."""

    __tablename__ = "event_links"
    __table_args__ = (
        UniqueConstraint("event_a_id", "event_b_id", name="uq_event_link_pair"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    # Canonical order: event_a_id holds the smaller id so the pair is unique.
    event_a_id: Mapped[str] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_b_id: Mapped[str] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )

    event_a: Mapped[Event] = relationship(foreign_keys=[event_a_id])
    event_b: Mapped[Event] = relationship(foreign_keys=[event_b_id])
