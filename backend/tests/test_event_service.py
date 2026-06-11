"""Direct service-layer tests for branches not fully driven via HTTP."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.schemas.event import EventCreate, EventUpdate, SessionCreate
from app.services.errors import NotFoundError
from app.services.event_service import EventService


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


def _evt() -> EventCreate:
    return EventCreate(
        name="Event",
        starts_at=datetime(2026, 6, 11, 9, tzinfo=timezone.utc),
        ends_at=datetime(2026, 6, 12, 17, tzinfo=timezone.utc),
    )


async def test_update_changes_times(session):
    svc = EventService(session)
    event = await svc.create_event(_evt())
    updated = await svc.update_event(
        event.id,
        EventUpdate(
            starts_at=datetime(2026, 6, 11, 8, tzinfo=timezone.utc),
            ends_at=datetime(2026, 6, 12, 18, tzinfo=timezone.utc),
        ),
    )
    assert updated.starts_at.hour == 8


async def test_get_missing_raises(session):
    with pytest.raises(NotFoundError):
        await EventService(session).get_event("missing")


async def test_add_session_returns_item(session):
    svc = EventService(session)
    event = await svc.create_event(_evt())
    item = await svc.add_session(
        event.id,
        SessionCreate(
            title="Talk",
            starts_at=datetime(2026, 6, 11, 10, tzinfo=timezone.utc),
            ends_at=datetime(2026, 6, 11, 11, tzinfo=timezone.utc),
        ),
    )
    assert item.title == "Talk"
    assert item.event_id == event.id
