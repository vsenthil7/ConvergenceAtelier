"""Webinar service (S7.4): capacity cap, waitlist, reminder schedule.

Built on the S3b EventRegistration layer. A webinar event carries its settings in
``Event.config``:
  - ``capacity``  : int seat cap (0 / missing = unlimited)
  - ``reminders`` : list of offset strings like ["24h", "1h", "15m"]
  - ``stream_url``: optional live link surfaced to registered attendees

Registration is capacity-aware: while seats remain the attendee is REGISTERED;
once full they are WAITLISTED. Cancelling a REGISTERED seat auto-promotes the
oldest WAITLISTED attendee. Everything is tenant-safe via EventService scoping.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.identity import User
from app.models.registration import EventRegistration, RegistrationStatus
from app.services.errors import NotFoundError
from app.services.event_service import EventService

_OFFSET_RE = re.compile(r"^(\d+)([dhm])$")
_UNIT_SECONDS = {"d": 86400, "h": 3600, "m": 60}


@dataclass(frozen=True)
class WebinarStatus:
    capacity: int  # 0 = unlimited
    registered_count: int
    waitlisted_count: int
    seats_left: int | None  # None when unlimited
    my_state: RegistrationStatus | None
    stream_url: str


@dataclass(frozen=True)
class WaitlistEntry:
    user_id: str
    email: str
    full_name: str
    position: int


@dataclass(frozen=True)
class Reminder:
    offset: str
    send_at: datetime


def _capacity(event: Event) -> int:
    raw = (event.config or {}).get("capacity", 0)
    try:
        cap = int(raw)
    except (TypeError, ValueError):
        return 0
    return max(cap, 0)


def parse_offset(token: str) -> timedelta | None:
    """Parse an offset like '24h' / '30m' / '2d' into a timedelta, else None."""
    match = _OFFSET_RE.match(token.strip().lower())
    if not match:
        return None
    value, unit = int(match.group(1)), match.group(2)
    return timedelta(seconds=value * _UNIT_SECONDS[unit])


class WebinarService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.events = EventService(session)

    async def _event(self, event_id: str, tenant_id: str | None) -> Event:
        return await self.events.get_event(event_id, tenant_id)

    async def _count(self, event_id: str, status: RegistrationStatus) -> int:
        return int(
            await self.session.scalar(
                select(func.count())
                .select_from(EventRegistration)
                .where(
                    EventRegistration.event_id == event_id,
                    EventRegistration.status == status,
                )
            )
            or 0
        )

    async def register(
        self, event_id: str, user: User, tenant_id: str | None
    ) -> EventRegistration:
        """Register for a webinar; overflow past capacity goes to the waitlist."""
        event = await self._event(event_id, tenant_id)
        capacity = _capacity(event)

        existing = await self.session.execute(
            select(EventRegistration).where(
                EventRegistration.event_id == event_id,
                EventRegistration.user_id == user.id,
            )
        )
        reg = existing.scalar_one_or_none()
        # An already-active row keeps its place (idempotent).
        if reg is not None and reg.status in (
            RegistrationStatus.REGISTERED,
            RegistrationStatus.WAITLISTED,
        ):
            return reg

        registered = await self._count(event_id, RegistrationStatus.REGISTERED)
        full = capacity > 0 and registered >= capacity
        new_status = (
            RegistrationStatus.WAITLISTED if full else RegistrationStatus.REGISTERED
        )
        if reg is None:
            reg = EventRegistration(
                event_id=event_id, user_id=user.id, status=new_status
            )
            self.session.add(reg)
        else:
            reg.status = new_status
        await self.session.commit()
        await self.session.refresh(reg)
        return reg

    async def cancel(
        self, event_id: str, user: User, tenant_id: str | None
    ) -> EventRegistration:
        """Cancel; if a seat frees up, auto-promote the oldest waitlisted attendee."""
        await self._event(event_id, tenant_id)
        existing = await self.session.execute(
            select(EventRegistration).where(
                EventRegistration.event_id == event_id,
                EventRegistration.user_id == user.id,
            )
        )
        reg = existing.scalar_one_or_none()
        if reg is None:
            raise NotFoundError("Registration", event_id)
        was_registered = reg.status is RegistrationStatus.REGISTERED
        reg.status = RegistrationStatus.CANCELLED
        await self.session.flush()

        if was_registered:
            await self._promote_one(event_id)
        await self.session.commit()
        await self.session.refresh(reg)
        return reg

    async def _promote_one(self, event_id: str) -> None:
        """Promote the oldest waitlisted attendee to REGISTERED, if any."""
        head = await self.session.execute(
            select(EventRegistration)
            .where(
                EventRegistration.event_id == event_id,
                EventRegistration.status == RegistrationStatus.WAITLISTED,
            )
            .order_by(EventRegistration.created_at, EventRegistration.id)
            .limit(1)
        )
        promote = head.scalar_one_or_none()
        if promote is not None:
            promote.status = RegistrationStatus.REGISTERED

    async def status(
        self, event_id: str, user: User, tenant_id: str | None
    ) -> WebinarStatus:
        event = await self._event(event_id, tenant_id)
        capacity = _capacity(event)
        registered = await self._count(event_id, RegistrationStatus.REGISTERED)
        waitlisted = await self._count(event_id, RegistrationStatus.WAITLISTED)
        mine = await self.session.execute(
            select(EventRegistration.status).where(
                EventRegistration.event_id == event_id,
                EventRegistration.user_id == user.id,
            )
        )
        my_state = mine.scalar_one_or_none()
        seats_left = None if capacity == 0 else max(capacity - registered, 0)
        return WebinarStatus(
            capacity=capacity,
            registered_count=registered,
            waitlisted_count=waitlisted,
            seats_left=seats_left,
            my_state=my_state,
            stream_url=str((event.config or {}).get("stream_url", "")),
        )

    async def waitlist(
        self, event_id: str, tenant_id: str | None
    ) -> list[WaitlistEntry]:
        """Ordered waitlist (admin-facing), oldest first."""
        await self._event(event_id, tenant_id)
        rows = await self.session.execute(
            select(EventRegistration, User)
            .join(User, User.id == EventRegistration.user_id)
            .where(
                EventRegistration.event_id == event_id,
                EventRegistration.status == RegistrationStatus.WAITLISTED,
            )
            .order_by(EventRegistration.created_at, EventRegistration.id)
        )
        return [
            WaitlistEntry(
                user_id=u.id,
                email=u.email,
                full_name=u.full_name,
                position=i + 1,
            )
            for i, (reg, u) in enumerate(rows.all())
        ]

    async def reminders(
        self, event_id: str, tenant_id: str | None
    ) -> list[Reminder]:
        """Absolute reminder send-times derived from config offsets before start."""
        event = await self._event(event_id, tenant_id)
        offsets = (event.config or {}).get("reminders", []) or []
        out: list[Reminder] = []
        for token in offsets:
            delta = parse_offset(str(token))
            if delta is not None:
                out.append(
                    Reminder(offset=str(token), send_at=event.starts_at - delta)
                )
        out.sort(key=lambda r: r.send_at)
        return out
