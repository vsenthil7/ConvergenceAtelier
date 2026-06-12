"""Demo seeder + config property coverage."""
from __future__ import annotations

from sqlalchemy import func, select

from app.config import Settings
from app.models.event import Event, EventType, Session, SessionMode
from app.models.hackathon import Submission, Team
from app.models.identity import Role, Tenant, User
from app.models.registration import EventRegistration, RegistrationStatus
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
    assert users == 8  # 1 super + 2 tenant-admins + 2 users + 3 webinar guests
    assert events == 4  # 2 conferences + 1 hackathon + 1 webinar
    assert sessions == 12  # 6 multi-track sessions per conference (typed events have none)
    assert supers == 1


async def test_seed_sessions_land_on_event_day(db):
    """Conference sessions must be scheduled on their event's opening day so the
    Scheduler (which opens on the event start date) renders them."""
    maker = db
    async with maker() as s:
        await seed_demo(s)
    async with maker() as s:
        events = (
            await s.execute(
                select(Event).where(Event.event_type == EventType.CONFERENCE)
            )
        ).scalars().all()
        for event in events:
            rows = (
                await s.execute(select(Session).where(Session.event_id == event.id))
            ).scalars().all()
            assert rows, "each conference should have sessions"
            for sess in rows:
                assert sess.starts_at.date() == event.starts_at.date()
            # Multi-track: more than one distinct track present.
            assert len({r.track for r in rows}) >= 2


async def test_seed_includes_demo_hackathon(db):
    """S7.3: the seed adds one hackathon-typed event with teams + scored submissions."""
    maker = db
    async with maker() as s:
        await seed_demo(s)
    async with maker() as s:
        hack = (
            await s.execute(
                select(Event).where(Event.event_type == EventType.HACKATHON)
            )
        ).scalar_one()
        teams = (
            await s.execute(select(Team).where(Team.event_id == hack.id))
        ).scalars().all()
        subs = (await s.execute(select(Submission))).scalars().all()
    assert hack.config.get("max_team_size") == 5
    assert {t.name for t in teams} == {"Falcons", "Eagles"}
    assert len(subs) == 2


async def test_seed_includes_demo_webinar(db):
    """S7.4: the seed adds one webinar-typed event with capacity + a waitlisted guest."""
    maker = db
    async with maker() as s:
        await seed_demo(s)
    async with maker() as s:
        webinar = (
            await s.execute(
                select(Event).where(Event.event_type == EventType.WEBINAR)
            )
        ).scalar_one()
        regs = (
            await s.execute(
                select(EventRegistration).where(
                    EventRegistration.event_id == webinar.id
                )
            )
        ).scalars().all()
    assert webinar.config.get("capacity") == 2
    assert webinar.config.get("reminders") == ["24h", "1h"]
    statuses = sorted(r.status.value for r in regs)
    assert statuses == ["registered", "registered", "waitlisted"]


async def test_seed_is_idempotent(db):
    maker = db
    async with maker() as s:
        assert await seed_demo(s) is True
    async with maker() as s:
        assert await seed_demo(s) is False


async def test_seed_includes_modes_and_recordings(db):
    """Demo agenda exercises S7.2: online/hybrid modes + some recordings."""
    maker = db
    async with maker() as s:
        await seed_demo(s)
    async with maker() as s:
        sessions = (await s.execute(select(Session))).scalars().all()
    modes = {sess.mode for sess in sessions}
    assert SessionMode.ONLINE in modes
    assert SessionMode.HYBRID in modes
    # at least one published recording across the demo set
    assert any(sess.recording_url for sess in sessions)
    # at least one live stream URL
    assert any(sess.stream_url for sess in sessions)


def test_google_oauth_enabled_property():
    assert Settings(google_client_id="", google_client_secret="").google_oauth_enabled is False
    assert (
        Settings(google_client_id="id", google_client_secret="secret").google_oauth_enabled
        is True
    )


def test_cors_origin_parsing():
    s = Settings(cors_origins="http://a.com, http://b.com ,, ")
    assert s.cors_origin_list == ["http://a.com", "http://b.com"]
