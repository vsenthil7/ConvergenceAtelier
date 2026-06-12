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
