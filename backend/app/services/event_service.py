"""Event + agenda session CRUD against the async session (tenant-scoped).

Every query is filtered by tenant. Super-admins pass tenant_id=None to span all
tenants; tenant-admins/users always pass their own tenant_id.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.event import Event, Session
from app.schemas.event import EventCreate, EventUpdate, SessionCreate
from app.services.errors import NotFoundError


class EventService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _scope(self, stmt, tenant_id: str | None):
        """Apply tenant filtering unless tenant_id is None (super-admin span)."""
        if tenant_id is not None:
            stmt = stmt.where(Event.tenant_id == tenant_id)
        return stmt

    async def list_events(self, tenant_id: str | None) -> list[Event]:
        stmt = self._scope(
            select(Event).options(selectinload(Event.sessions)).order_by(Event.starts_at),
            tenant_id,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_event(self, event_id: str, tenant_id: str | None) -> Event:
        stmt = self._scope(
            select(Event).options(selectinload(Event.sessions)).where(Event.id == event_id),
            tenant_id,
        )
        result = await self.session.execute(stmt)
        event = result.scalar_one_or_none()
        if event is None:
            raise NotFoundError("Event", event_id)
        return event

    async def create_event(self, tenant_id: str, data: EventCreate) -> Event:
        event = Event(
            tenant_id=tenant_id,
            name=data.name,
            location=data.location,
            description=data.description,
            event_type=data.event_type,
            config=data.config,
            starts_at=data.starts_at,
            ends_at=data.ends_at,
        )
        self.session.add(event)
        await self.session.commit()
        return await self.get_event(event.id, tenant_id)

    async def update_event(
        self, event_id: str, tenant_id: str | None, data: EventUpdate
    ) -> Event:
        event = await self.get_event(event_id, tenant_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(event, field, value)
        await self.session.commit()
        return await self.get_event(event_id, tenant_id)

    async def delete_event(self, event_id: str, tenant_id: str | None) -> None:
        event = await self.get_event(event_id, tenant_id)
        await self.session.delete(event)
        await self.session.commit()

    async def add_session(
        self, event_id: str, tenant_id: str | None, data: SessionCreate
    ) -> Session:
        await self.get_event(event_id, tenant_id)  # ensures event exists & in scope
        agenda_item = Session(
            event_id=event_id,
            title=data.title,
            track=data.track,
            speaker=data.speaker,
            starts_at=data.starts_at,
            ends_at=data.ends_at,
        )
        self.session.add(agenda_item)
        await self.session.commit()
        await self.session.refresh(agenda_item)
        return agenda_item
