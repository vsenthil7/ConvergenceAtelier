"""Timezone-aware SQLAlchemy base.

Pre-mitigation: every timestamp column is TIMESTAMP WITH TIME ZONE and every
generated default is an aware UTC datetime, so the app never mixes naive and
aware datetimes (the failure that cost a prior project ~1.5h).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    """Return the current time as an aware UTC datetime."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Declarative base; all timestamp columns must use ``AwareDateTime``."""


# Always store/compare timezone-aware datetimes.
AwareDateTime = DateTime(timezone=True)


class TimestampMixin:
    """Adds tz-aware created_at / updated_at to a model."""

    created_at: Mapped[datetime] = mapped_column(
        AwareDateTime, default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        AwareDateTime, default=utcnow, onupdate=utcnow, nullable=False
    )
