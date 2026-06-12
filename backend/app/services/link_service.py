"""Event link service (S7.5): connect events into a series + combined catalog.

Links are symmetric and stored in canonical order (smaller id first). Both
events must be in the caller's tenant (enforced via EventService scoping). The
combined catalog returns every session across an event and its linked events,
each tagged with its source event, ordered by start time.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event, Session
from app.models.link import EventLink
from app.services.errors import ConflictError, NotFoundError
from app.services.event_service import EventService


@dataclass(frozen=True)
class CatalogSession:
    """A session in the combined catalog, tagged with its source event."""

    session_id: str
    event_id: str
    event_name: str
    title: str
    track: str
    speaker: str
    mode: str
    stream_url: str
    recording_url: str
    starts_at: object  # datetime; kept loose for the schema layer


def _canonical(a: str, b: str) -> tuple[str, str]:
    """Order a pair so the smaller id is first (links are unordered)."""
    return (a, b) if a <= b else (b, a)


class LinkService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.events = EventService(session)

    async def link(
        self, event_id: str, other_id: str, tenant_id: str | None
    ) -> EventLink:
        """Link two events (both must be in scope). Self-link rejected; dup ok."""
        if event_id == other_id:
            raise ConflictError("EventLink", "cannot link an event to itself")
        # Both must exist and be in the caller's tenant.
        await self.events.get_event(event_id, tenant_id)
        await self.events.get_event(other_id, tenant_id)

        a, b = _canonical(event_id, other_id)
        existing = await self.session.execute(
            select(EventLink).where(
                EventLink.event_a_id == a, EventLink.event_b_id == b
            )
        )
        link = existing.scalar_one_or_none()
        if link is not None:
            raise ConflictError("EventLink", f"{a}+{b}")
        link = EventLink(event_a_id=a, event_b_id=b)
        self.session.add(link)
        await self.session.commit()
        await self.session.refresh(link)
        return link

    async def unlink(
        self, event_id: str, other_id: str, tenant_id: str | None
    ) -> None:
        """Remove a link between two events (must exist and be in scope)."""
        await self.events.get_event(event_id, tenant_id)
        a, b = _canonical(event_id, other_id)
        existing = await self.session.execute(
            select(EventLink).where(
                EventLink.event_a_id == a, EventLink.event_b_id == b
            )
        )
        link = existing.scalar_one_or_none()
        if link is None:
            raise NotFoundError("EventLink", f"{a}+{b}")
        await self.session.delete(link)
        await self.session.commit()

    async def _linked_ids(self, event_id: str) -> list[str]:
        """Ids of events linked to the given event (either side of the pair)."""
        rows = await self.session.execute(
            select(EventLink).where(
                or_(EventLink.event_a_id == event_id, EventLink.event_b_id == event_id)
            )
        )
        ids: list[str] = []
        for link in rows.scalars().all():
            ids.append(link.event_b_id if link.event_a_id == event_id else link.event_a_id)
        return ids

    async def linked_events(
        self, event_id: str, tenant_id: str | None
    ) -> list[Event]:
        """Events linked to this one (in-scope only), ordered by start time."""
        await self.events.get_event(event_id, tenant_id)
        ids = await self._linked_ids(event_id)
        if not ids:
            return []
        stmt = select(Event).where(Event.id.in_(ids)).order_by(Event.starts_at)
        if tenant_id is not None:
            stmt = stmt.where(Event.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def catalog(
        self, event_id: str, tenant_id: str | None
    ) -> list[CatalogSession]:
        """Combined session catalog across this event + its linked events."""
        event = await self.events.get_event(event_id, tenant_id)
        ids = [event_id, *await self._linked_ids(event_id)]
        # Map event id -> name for tagging (in-scope events only).
        name_stmt = select(Event).where(Event.id.in_(ids))
        if tenant_id is not None:
            name_stmt = name_stmt.where(Event.tenant_id == tenant_id)
        events = {e.id: e for e in (await self.session.execute(name_stmt)).scalars().all()}

        stmt = (
            select(Session)
            .where(Session.event_id.in_(list(events.keys())))
            .order_by(Session.starts_at)
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return [
            CatalogSession(
                session_id=s.id,
                event_id=s.event_id,
                event_name=events[s.event_id].name,
                title=s.title,
                track=s.track,
                speaker=s.speaker,
                mode=s.mode.value,
                stream_url=s.stream_url,
                recording_url=s.recording_url,
                starts_at=s.starts_at,
            )
            for s in rows
        ]
