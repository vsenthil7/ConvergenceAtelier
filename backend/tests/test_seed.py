"""Demo seeder + config property coverage."""
from __future__ import annotations

from sqlalchemy import func, select

from app.config import Settings
from app.models.event import Event, Session
from app.models.identity import Role, Tenant, User
from app.services.seed import seed_demo


async def test_seed_creates_demo_data(db):
    maker = db
    async with maker() as s:
        seeded = await seed_demo(s)
    assert seeded is True
    async with maker() as s:
        tenants = await s.scalar(select(func.count()).select_from(Tenant))
        users = await s.scalar(select(func.count()).select_from(User))
        events = await s.scalar(select(func.count()).select_from(Event))
        sessions = await s.scalar(select(func.count()).select_from(Session))
        supers = await s.scalar(
            select(func.count()).select_from(User).where(User.role == Role.SUPER_ADMIN)
        )
    assert tenants == 2
    assert users == 5  # 1 super + 2 tenant-admins + 2 users
    assert events == 2
    assert sessions == 12  # 6 multi-track sessions per event
    assert supers == 1


async def test_seed_sessions_land_on_event_day(db):
    """Sessions must be scheduled on their event's opening day so the Scheduler
    (which opens on the event start date) renders them."""
    maker = db
    async with maker() as s:
        await seed_demo(s)
    async with maker() as s:
        events = (await s.execute(select(Event))).scalars().all()
        for event in events:
            rows = (
                await s.execute(select(Session).where(Session.event_id == event.id))
            ).scalars().all()
            assert rows, "each event should have sessions"
            for sess in rows:
                assert sess.starts_at.date() == event.starts_at.date()
            # Multi-track: more than one distinct track present.
            assert len({r.track for r in rows}) >= 2


async def test_seed_is_idempotent(db):
    maker = db
    async with maker() as s:
        assert await seed_demo(s) is True
    async with maker() as s:
        assert await seed_demo(s) is False


def test_google_oauth_enabled_property():
    assert Settings(google_client_id="", google_client_secret="").google_oauth_enabled is False
    assert (
        Settings(google_client_id="id", google_client_secret="secret").google_oauth_enabled
        is True
    )


def test_cors_origin_parsing():
    s = Settings(cors_origins="http://a.com, http://b.com ,, ")
    assert s.cors_origin_list == ["http://a.com", "http://b.com"]
