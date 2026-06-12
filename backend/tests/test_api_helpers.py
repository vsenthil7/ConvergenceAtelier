"""Direct API-handler tests for deterministic coverage of route helper bodies
that the ASGI transport traces unreliably under full-suite load.
"""
from __future__ import annotations

import pytest

from app.api.events import _read_scope, _write_tenant
from app.models.identity import Role, User
from app.services.errors import ForbiddenError


def test_read_scope_super_admin_spans_all():
    su = User(email="s@x.com", role=Role.SUPER_ADMIN, tenant_id=None)
    assert _read_scope(su) is None


def test_read_scope_tenant_user_scoped():
    u = User(email="u@x.com", role=Role.USER, tenant_id="t1")
    assert _read_scope(u) == "t1"


def test_write_tenant_returns_tenant():
    admin = User(email="a@x.com", role=Role.TENANT_ADMIN, tenant_id="t1")
    assert _write_tenant(admin) == "t1"


def test_write_tenant_without_tenant_raises():
    su = User(email="s@x.com", role=Role.SUPER_ADMIN, tenant_id=None)
    with pytest.raises(ForbiddenError):
        _write_tenant(su)


async def test_auth_routes_called_directly(db):
    """Cover the login + google + config route bodies deterministically."""
    from app.api.auth import auth_config, login, login_google
    from app.schemas.auth import GoogleLoginRequest, LoginRequest
    from app.services.auth_service import AuthService
    from app.schemas.auth import UserCreate

    maker = db
    async with maker() as s:
        svc = AuthService(s)
        await svc.create_user(
            UserCreate(email="a@x.com", password="password1", role=Role.USER)
        )

    # login route body
    async with maker() as s:
        svc = AuthService(s)
        token = await login(LoginRequest(email="a@x.com", password="password1"), svc=svc)
        assert token.access_token

    # google route body (verifier injected)
    async def good(_):
        return {"email": "g2@x.com", "name": "G2"}

    async with maker() as s:
        svc = AuthService(s, google_verifier=good)
        gtoken = await login_google(GoogleLoginRequest(id_token="tok"), svc=svc)
        assert gtoken.access_token

    # config route body
    cfg = await auth_config()
    assert "google_enabled" in cfg


async def test_event_routes_called_directly(db):
    """Cover the event route handler bodies (incl. non-empty list comprehension)."""
    from app.api.events import (
        add_session,
        create_event,
        delete_event,
        get_event,
        list_events,
        update_event,
    )
    from app.schemas.event import EventCreate, EventUpdate, SessionCreate
    from app.services.event_service import EventService
    from app.models.identity import Tenant
    from datetime import datetime, timezone

    maker = db
    async with maker() as s:
        t = Tenant(name="Org", slug="org")
        s.add(t)
        await s.commit()
        await s.refresh(t)
        tid = t.id

    admin = User(email="a@x.com", role=Role.TENANT_ADMIN, tenant_id=tid)
    plain = User(email="u@x.com", role=Role.USER, tenant_id=tid)
    evt = EventCreate(
        name="Conf",
        starts_at=datetime(2026, 6, 11, 9, tzinfo=timezone.utc),
        ends_at=datetime(2026, 6, 12, 17, tzinfo=timezone.utc),
    )

    async with maker() as s:
        svc = EventService(s)
        created = await create_event(evt, user=admin, svc=svc)
        eid = created.id

    # list returns a NON-empty list -> exercises the comprehension element.
    async with maker() as s:
        svc = EventService(s)
        listing = await list_events(user=admin, svc=svc)
        assert len(listing) == 1
        fetched = await get_event(eid, user=admin, svc=svc)
        assert fetched.id == eid
        updated = await update_event(eid, EventUpdate(name="New"), user=admin, svc=svc)
        assert updated.name == "New"
        item = await add_session(
            eid,
            SessionCreate(
                title="Talk",
                starts_at=datetime(2026, 6, 11, 10, tzinfo=timezone.utc),
                ends_at=datetime(2026, 6, 11, 11, tzinfo=timezone.utc),
            ),
            user=admin,
            svc=svc,
        )
        assert item.title == "Talk"

    # RBAC: a USER role is forbidden from each write handler.
    async with maker() as s:
        svc = EventService(s)
        for coro in (
            create_event(evt, user=plain, svc=svc),
            update_event(eid, EventUpdate(name="x"), user=plain, svc=svc),
            delete_event(eid, user=plain, svc=svc),
            add_session(
                eid,
                SessionCreate(
                    title="T",
                    starts_at=datetime(2026, 6, 11, 10, tzinfo=timezone.utc),
                    ends_at=datetime(2026, 6, 11, 11, tzinfo=timezone.utc),
                ),
                user=plain,
                svc=svc,
            ),
        ):
            with pytest.raises(ForbiddenError):
                await coro

    # delete by the admin (covers the delete handler success path).
    async with maker() as s:
        svc = EventService(s)
        await delete_event(eid, user=admin, svc=svc)


def test_discovery_read_scope_helpers():
    """Cover the discovery route's tenant-scope helper on both branches."""
    from app.api.discovery import _read_scope as disc_scope

    su = User(email="s@x.com", role=Role.SUPER_ADMIN, tenant_id=None)
    u = User(email="u@x.com", role=Role.USER, tenant_id="t1")
    assert disc_scope(su) is None
    assert disc_scope(u) == "t1"


async def test_discovery_routes_called_directly(db):
    """Cover the discovery route handler bodies deterministically."""
    from datetime import datetime, timezone

    from app.api.discovery import (
        draft_agenda,
        match_attendees,
        recommend_for_interests,
        similar_sessions,
    )
    from app.models.event import Event, Session
    from app.models.identity import Tenant
    from app.schemas.discovery import (
        AgendaDraftRequest,
        AttendeeProfileIn,
        InterestQuery,
        MatchRequest,
    )
    from app.services.discovery_service import DiscoveryService

    maker = db
    async with maker() as s:
        t = Tenant(name="Org", slug="org")
        s.add(t)
        await s.flush()
        tid = t.id
        ev = Event(
            tenant_id=tid,
            name="Conf",
            starts_at=datetime(2026, 6, 11, 9, tzinfo=timezone.utc),
            ends_at=datetime(2026, 6, 12, 17, tzinfo=timezone.utc),
        )
        s.add(ev)
        await s.flush()
        s.add_all(
            [
                Session(
                    event_id=ev.id, title="React hooks", track="FE", speaker="Ada",
                    starts_at=datetime(2026, 6, 11, 10, tzinfo=timezone.utc),
                    ends_at=datetime(2026, 6, 11, 11, tzinfo=timezone.utc),
                ),
                Session(
                    event_id=ev.id, title="More React hooks", track="FE", speaker="Lin",
                    starts_at=datetime(2026, 6, 11, 11, tzinfo=timezone.utc),
                    ends_at=datetime(2026, 6, 11, 12, tzinfo=timezone.utc),
                ),
            ]
        )
        await s.commit()
        first_id = (await s.execute(__import__("sqlalchemy").select(Session.id)))
        sid = first_id.scalars().first()
        eid_for_draft = ev.id

    admin = User(email="a@x.com", role=Role.TENANT_ADMIN, tenant_id=tid)

    async with maker() as s:
        svc = DiscoveryService(s)
        sim = await similar_sessions(sid, limit=5, user=admin, svc=svc)
        assert isinstance(sim, list)
        rec = await recommend_for_interests(
            InterestQuery(interests="react hooks", limit=2), user=admin, svc=svc
        )
        assert len(rec) >= 1
        matches = await match_attendees(
            MatchRequest(
                attendees=[
                    AttendeeProfileIn(id="1", name="A", interests="react"),
                    AttendeeProfileIn(id="2", name="B", interests="react"),
                ],
                limit=5,
            ),
            user=admin,
            svc=svc,
        )
        assert matches and {matches[0].a.id, matches[0].b.id} == {"1", "2"}
        # agenda-draft handler body (covers the AgendaSlotRead comprehension).
        draft = await draft_agenda(
            eid_for_draft,
            AgendaDraftRequest(theme="react hooks"),
            user=admin,
            svc=svc,
        )
        assert draft and draft[0].order == 0


def test_ai_live_enabled_property():
    """Cover the Settings.ai_live_enabled branches."""
    from app.config import Settings

    off = Settings(ai_api_key="", use_mocks=True)
    assert off.ai_live_enabled is False
    # key present but mocks still on -> still disabled
    mocked = Settings(ai_api_key="sk-test", use_mocks=True)
    assert mocked.ai_live_enabled is False
    # key present and mocks off -> enabled
    live = Settings(ai_api_key="sk-test", use_mocks=False)
    assert live.ai_live_enabled is True


async def test_register_route_called_directly(seeded):
    """Cover the public-register route body + register_public service path."""
    from app.api.auth import register
    from app.schemas.auth import PublicRegister
    from app.services.auth_service import AuthService

    maker = seeded["maker"]
    async with maker() as s:
        svc = AuthService(s)
        token = await register(
            PublicRegister(
                email="direct@x.com",
                full_name="Direct",
                password="Secret123!",
                tenant_slug="react-org",
            ),
            svc=svc,
        )
    assert token.access_token


async def test_registration_routes_called_directly(seeded):
    """Cover the four registration route handler bodies deterministically."""
    from app.api.events import (
        cancel_registration,
        event_participants,
        my_registration,
        register_for_event,
    )
    from app.models.identity import User
    from app.services.registration_service import RegistrationService
    from tests.conftest import make_event

    maker = seeded["maker"]
    t1 = seeded["ids"]["t1"]
    event_id = await make_event(maker, t1, name="Conf")
    attendee = User(id=seeded["ids"]["u1"], email="u1@x.com", role=Role.USER, tenant_id=t1)
    admin = User(id=seeded["ids"]["a1"], email="a1@x.com", role=Role.TENANT_ADMIN, tenant_id=t1)
    plain = User(id=seeded["ids"]["u1"], email="u1@x.com", role=Role.USER, tenant_id=t1)

    async with maker() as s:
        svc = RegistrationService(s)
        reg = await register_for_event(event_id, user=attendee, svc=svc)
        assert reg.status.value == "registered"
        status = await my_registration(event_id, user=attendee, svc=svc)
        assert status.status is not None
        roster = await event_participants(event_id, user=admin, svc=svc)
        assert len(roster) == 1
        cancelled = await cancel_registration(event_id, user=attendee, svc=svc)
        assert cancelled.status.value == "cancelled"

    # RBAC: a plain USER cannot read the roster.
    async with maker() as s:
        svc = RegistrationService(s)
        with pytest.raises(ForbiddenError):
            await event_participants(event_id, user=plain, svc=svc)


async def test_recordings_route_called_directly(seeded):
    """Cover the recordings route body + list_recordings service path (S7.2)."""
    from app.api.events import add_session, event_recordings
    from app.models.identity import User
    from app.schemas.event import SessionCreate
    from app.services.event_service import EventService
    from tests.conftest import make_event
    from datetime import datetime, timezone

    maker = seeded["maker"]
    t1 = seeded["ids"]["t1"]
    event_id = await make_event(maker, t1, name="Conf")
    admin = User(id=seeded["ids"]["a1"], email="a1@x.com", role=Role.TENANT_ADMIN, tenant_id=t1)

    async with maker() as s:
        svc = EventService(s)
        await add_session(
            event_id,
            SessionCreate(
                title="Recorded",
                starts_at=datetime(2026, 6, 11, 10, tzinfo=timezone.utc),
                ends_at=datetime(2026, 6, 11, 11, tzinfo=timezone.utc),
                recording_url="https://rec.example/z",
            ),
            user=admin,
            svc=svc,
        )
        rows = await event_recordings(event_id, user=admin, svc=svc)
        assert len(rows) == 1
        assert rows[0].recording_url == "https://rec.example/z"


async def test_hackathon_routes_called_directly(seeded):
    """Cover every hackathon route handler body deterministically (S7.3)."""
    from app.api.hackathon import (
        create_submission,
        create_team,
        join_team,
        leaderboard,
        list_submissions,
        list_teams,
        record_score,
        update_submission,
    )
    from app.models.identity import User
    from app.schemas.hackathon import (
        ScoreCreate,
        SubmissionCreate,
        SubmissionUpdate,
        TeamCreate,
    )
    from app.services.hackathon_service import HackathonService
    from tests.conftest import make_event

    maker = seeded["maker"]
    t1 = seeded["ids"]["t1"]
    eid = await make_event(maker, t1, name="Hack")
    attendee = User(id=seeded["ids"]["u1"], email="u1@x.com", role=Role.USER, tenant_id=t1)
    judge = User(id=seeded["ids"]["a1"], email="a1@x.com", role=Role.TENANT_ADMIN, tenant_id=t1)
    plain = User(id=seeded["ids"]["u1"], email="u1@x.com", role=Role.USER, tenant_id=t1)

    async with maker() as s:
        svc = HackathonService(s)
        team = await create_team(eid, TeamCreate(name="Falcons"), user=attendee, svc=svc)
        team_id = team.id
        joined = await join_team(eid, team_id, user=attendee, svc=svc)
        assert len(joined.members) == 1
        teams = await list_teams(eid, user=attendee, svc=svc)
        assert len(teams) == 1
        sub = await create_submission(
            eid, team_id, SubmissionCreate(title="Alpha"), user=attendee, svc=svc
        )
        sub_id = sub.id
        patched = await update_submission(
            eid, sub_id, SubmissionUpdate(title="Alpha2"), user=attendee, svc=svc
        )
        assert patched.title == "Alpha2"
        subs = await list_submissions(eid, user=attendee, svc=svc)
        assert len(subs) == 1

    async with maker() as s:
        svc = HackathonService(s)
        score = await record_score(
            eid, sub_id, ScoreCreate(criterion="impact", value=8), user=judge, svc=svc
        )
        assert score.value == 8
        board = await leaderboard(eid, user=judge, svc=svc)
        assert board[0].rank == 1
        assert board[0].total_score == 8

    # RBAC: a plain USER cannot score.
    async with maker() as s:
        svc = HackathonService(s)
        with pytest.raises(ForbiddenError):
            await record_score(
                eid, sub_id, ScoreCreate(criterion="impact", value=5), user=plain, svc=svc
            )


async def test_webinar_routes_called_directly(seeded):
    """Cover every webinar route handler body deterministically (S7.4)."""
    from datetime import datetime, timezone

    from app.api.webinar import (
        webinar_cancel,
        webinar_register,
        webinar_reminders,
        webinar_status,
        webinar_waitlist,
    )
    from app.models.event import Event, EventType
    from app.models.identity import User
    from app.services.webinar_service import WebinarService

    maker = seeded["maker"]
    t1 = seeded["ids"]["t1"]
    async with maker() as s:
        e = Event(
            tenant_id=t1, name="W", event_type=EventType.WEBINAR,
            config={"capacity": 1, "reminders": ["1h"], "stream_url": "https://s/x"},
            starts_at=datetime(2026, 7, 1, 17, tzinfo=timezone.utc),
            ends_at=datetime(2026, 7, 1, 18, tzinfo=timezone.utc),
        )
        s.add(e)
        await s.commit()
        await s.refresh(e)
        eid = e.id

    attendee = User(id=seeded["ids"]["u1"], email="u1@x.com", role=Role.USER, tenant_id=t1)
    admin = User(id=seeded["ids"]["a1"], email="a1@x.com", role=Role.TENANT_ADMIN, tenant_id=t1)

    async with maker() as s:
        svc = WebinarService(s)
        reg = await webinar_register(eid, user=attendee, svc=svc)
        assert reg.status.value == "registered"
        st = await webinar_status(eid, user=attendee, svc=svc)
        assert st.registered_count == 1
        rem = await webinar_reminders(eid, user=attendee, svc=svc)
        assert rem and rem[0].offset == "1h"
        wl = await webinar_waitlist(eid, user=admin, svc=svc)
        assert wl == []
        cancelled = await webinar_cancel(eid, user=attendee, svc=svc)
        assert cancelled.status.value == "cancelled"

    # RBAC: a plain USER cannot read the waitlist.
    async with maker() as s:
        svc = WebinarService(s)
        with pytest.raises(ForbiddenError):
            await webinar_waitlist(eid, user=attendee, svc=svc)


async def test_link_routes_called_directly(seeded):
    """Cover every event-link route handler body deterministically (S7.5)."""
    from app.api.links import (
        combined_catalog,
        create_link,
        list_links,
        remove_link,
    )
    from app.models.identity import User
    from app.schemas.link import LinkRequest
    from app.services.link_service import LinkService
    from tests.conftest import make_event, make_session

    maker = seeded["maker"]
    t1 = seeded["ids"]["t1"]
    e1 = await make_event(maker, t1, "Flagship")
    e2 = await make_event(maker, t1, "Online")
    await make_session(maker, e1, title="In-person Talk")
    await make_session(maker, e2, title="Online Talk")
    admin = User(id=seeded["ids"]["a1"], email="a1@x.com", role=Role.TENANT_ADMIN, tenant_id=t1)
    plain = User(id=seeded["ids"]["u1"], email="u1@x.com", role=Role.USER, tenant_id=t1)

    async with maker() as s:
        svc = LinkService(s)
        linked = await create_link(e1, LinkRequest(other_event_id=e2), user=admin, svc=svc)
        assert [e.id for e in linked] == [e2]
        listing = await list_links(e1, user=admin, svc=svc)
        assert [e.id for e in listing] == [e2]
        catalog = await combined_catalog(e1, user=admin, svc=svc)
        assert {c.title for c in catalog} == {"In-person Talk", "Online Talk"}
        after = await remove_link(e1, e2, user=admin, svc=svc)
        assert after == []

    # RBAC: a plain USER cannot link or unlink.
    async with maker() as s:
        svc = LinkService(s)
        with pytest.raises(ForbiddenError):
            await create_link(e1, LinkRequest(other_event_id=e2), user=plain, svc=svc)
        with pytest.raises(ForbiddenError):
            await remove_link(e1, e2, user=plain, svc=svc)


async def test_plan_route_called_directly(seeded):
    """Cover the plan route handler body deterministically (S7.6)."""
    from datetime import datetime, timezone

    from app.api.discovery import draft_plan
    from app.models.event import Event, EventType
    from app.models.identity import User
    from app.schemas.discovery import PlanDraftRequest
    from app.services.plan_service import PlanService

    maker = seeded["maker"]
    t1 = seeded["ids"]["t1"]
    async with maker() as s:
        e = Event(
            tenant_id=t1, name="Hack", event_type=EventType.HACKATHON,
            starts_at=datetime(2026, 7, 1, 9, tzinfo=timezone.utc),
            ends_at=datetime(2026, 7, 3, 17, tzinfo=timezone.utc),
        )
        s.add(e)
        await s.commit()
        await s.refresh(e)
        eid = e.id

    user = User(id=seeded["ids"]["u1"], email="u1@x.com", role=Role.USER, tenant_id=t1)
    async with maker() as s:
        svc = PlanService(s)
        rows = await draft_plan(eid, PlanDraftRequest(theme="judging"), user=user, svc=svc)
    assert [r.key for r in rows][0] == "registration"
    assert all(0.0 <= r.relevance <= 1.0 for r in rows)
