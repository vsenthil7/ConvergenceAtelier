"""Event registration service (S3b): attendee self-service + admin roster.

Registration is tenant-safe: an attendee may only register for events in their
own tenant; super-admins span all tenants. The (event, user) pair is unique, so
re-registering after cancelling flips the existing row back to REGISTERED rather
than creating a duplicate.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.identity import User
from app.models.registration import EventRegistration, RegistrationStatus
from app.services.errors import NotFoundError
from app.services.event_service import EventService


@dataclass(frozen=True)
class Participant:
    """A registered attendee (projection for the roster)."""

    user_id: str
    email: str
    full_name: str
    status: RegistrationStatus


class RegistrationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.events = EventService(session)

    async def _event_in_scope(self, event_id: str, tenant_id: str | None) -> Event:
        # Reuses EventService scoping (raises NotFound if outside the caller's tenant).
        return await self.events.get_event(event_id, tenant_id)

    async def register(
        self, event_id: str, user: User, tenant_id: str | None
    ) -> EventRegistration:
        """Register the current user for an event (idempotent re-activate)."""
        await self._event_in_scope(event_id, tenant_id)
        existing = await self.session.execute(
            select(EventRegistration).where(
                EventRegistration.event_id == event_id,
                EventRegistration.user_id == user.id,
            )
        )
        reg = existing.scalar_one_or_none()
        if reg is None:
            reg = EventRegistration(
                event_id=event_id,
                user_id=user.id,
                status=RegistrationStatus.REGISTERED,
            )
            self.session.add(reg)
        else:
            reg.status = RegistrationStatus.REGISTERED
        await self.session.commit()
        await self.session.refresh(reg)
        return reg

    async def cancel(
        self, event_id: str, user: User, tenant_id: str | None
    ) -> EventRegistration:
        """Cancel the current user's registration (must exist)."""
        await self._event_in_scope(event_id, tenant_id)
        existing = await self.session.execute(
            select(EventRegistration).where(
                EventRegistration.event_id == event_id,
                EventRegistration.user_id == user.id,
            )
        )
        reg = existing.scalar_one_or_none()
        if reg is None:
            raise NotFoundError("Registration", event_id)
        reg.status = RegistrationStatus.CANCELLED
        await self.session.commit()
        await self.session.refresh(reg)
        return reg

    async def my_status(
        self, event_id: str, user: User, tenant_id: str | None
    ) -> RegistrationStatus | None:
        """The current user's status for an event, or None if never registered."""
        await self._event_in_scope(event_id, tenant_id)
        existing = await self.session.execute(
            select(EventRegistration).where(
                EventRegistration.event_id == event_id,
                EventRegistration.user_id == user.id,
            )
        )
        reg = existing.scalar_one_or_none()
        return reg.status if reg is not None else None

    async def participants(
        self, event_id: str, tenant_id: str | None
    ) -> list[Participant]:
        """Roster of REGISTERED attendees for an event (admin-facing)."""
        await self._event_in_scope(event_id, tenant_id)
        stmt = (
            select(EventRegistration, User)
            .join(User, User.id == EventRegistration.user_id)
            .where(
                EventRegistration.event_id == event_id,
                EventRegistration.status == RegistrationStatus.REGISTERED,
            )
            .order_by(User.email)
        )
        result = await self.session.execute(stmt)
        return [
            Participant(
                user_id=u.id,
                email=u.email,
                full_name=u.full_name,
                status=reg.status,
            )
            for reg, u in result.all()
        ]
