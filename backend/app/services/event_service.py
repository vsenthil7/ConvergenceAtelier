"""Event + agenda session CRUD against the async session."""
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

    async def list_events(self) -> list[Event]:
        result = await self.session.execute(
            select(Event).options(selectinload(Event.sessions)).order_by(Event.starts_at)
        )
        return list(result.scalars().all())

    async def get_event(self, event_id: str) -> Event:
        result = await self.session.execute(
            select(Event).options(selectinload(Event.sessions)).where(Event.id == event_id)
        )
        event = result.scalar_one_or_none()
        if event is None:
            raise NotFoundError("Event", event_id)
        return event

    async def create_event(self, data: EventCreate) -> Event:
        event = Event(
            name=data.name,
            location=data.location,
            description=data.description,
            starts_at=data.starts_at,
            ends_at=data.ends_at,
        )
        self.session.add(event)
        await self.session.commit()
        return await self.get_event(event.id)

    async def update_event(self, event_id: str, data: EventUpdate) -> Event:
        event = await self.get_event(event_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(event, field, value)
        await self.session.commit()
        return await self.get_event(event_id)

    async def delete_event(self, event_id: str) -> None:
        event = await self.get_event(event_id)
        await self.session.delete(event)
        await self.session.commit()

    async def add_session(self, event_id: str, data: SessionCreate) -> Session:
        await self.get_event(event_id)  # ensures event exists (raises if not)
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
