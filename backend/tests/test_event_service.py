"""Direct service-layer tests for tenant-scoped branches."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models.identity import Tenant
from app.schemas.event import EventCreate, EventUpdate, SessionCreate
from app.services.errors import NotFoundError
from app.services.event_service import EventService


@pytest.fixture
async def session_and_tenant():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        t = Tenant(name="Org", slug="org")
        s.add(t)
        await s.commit()
        await s.refresh(t)
        yield s, t.id
    await engine.dispose()


def _evt() -> EventCreate:
    return EventCreate(
        name="Event",
        starts_at=datetime(2026, 6, 11, 9, tzinfo=timezone.utc),
        ends_at=datetime(2026, 6, 12, 17, tzinfo=timezone.utc),
    )


async def test_create_then_list_scoped(session_and_tenant):
    s, tid = session_and_tenant
    svc = EventService(s)
    await svc.create_event(tid, _evt())
    events = await svc.list_events(tid)
    assert len(events) == 1


async def test_super_admin_span_lists_all(session_and_tenant):
    s, tid = session_and_tenant
    svc = EventService(s)
    await svc.create_event(tid, _evt())
    # tenant_id=None spans all tenants
    assert len(await svc.list_events(None)) == 1


async def test_update_changes_times(session_and_tenant):
    s, tid = session_and_tenant
    svc = EventService(s)
    event = await svc.create_event(tid, _evt())
    updated = await svc.update_event(
        event.id,
        tid,
        EventUpdate(
            starts_at=datetime(2026, 6, 11, 8, tzinfo=timezone.utc),
            ends_at=datetime(2026, 6, 12, 18, tzinfo=timezone.utc),
        ),
    )
    assert updated.starts_at.hour == 8


async def test_delete_removes_event(session_and_tenant):
    s, tid = session_and_tenant
    svc = EventService(s)
    event = await svc.create_event(tid, _evt())
    await svc.delete_event(event.id, tid)
    assert await svc.list_events(tid) == []


async def test_get_missing_raises(session_and_tenant):
    s, tid = session_and_tenant
    with pytest.raises(NotFoundError):
        await EventService(s).get_event("missing", tid)


async def test_delete_missing_raises(session_and_tenant):
    s, tid = session_and_tenant
    with pytest.raises(NotFoundError):
        await EventService(s).delete_event("missing", tid)


async def test_add_session_returns_item(session_and_tenant):
    s, tid = session_and_tenant
    svc = EventService(s)
    event = await svc.create_event(tid, _evt())
    item = await svc.add_session(
        event.id,
        tid,
        SessionCreate(
            title="Talk",
            starts_at=datetime(2026, 6, 11, 10, tzinfo=timezone.utc),
            ends_at=datetime(2026, 6, 11, 11, tzinfo=timezone.utc),
        ),
    )
    assert item.title == "Talk"
