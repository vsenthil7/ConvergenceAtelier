"""Direct WebinarService tests (deterministic, no ASGI) — closes service coverage
and the offset parser."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models.event import Event, EventType
from app.models.identity import Role, User
from app.models.registration import EventRegistration, RegistrationStatus
from app.services.errors import NotFoundError
from app.services.webinar_service import WebinarService, parse_offset


def test_parse_offset_units_and_invalid():
    assert parse_offset("24h").total_seconds() == 24 * 3600
    assert parse_offset("30m").total_seconds() == 30 * 60
    assert parse_offset("2d").total_seconds() == 2 * 86400
    assert parse_offset("bogus") is None
    assert parse_offset("10s") is None  # unsupported unit


async def _webinar(maker, tenant_id, capacity=2, reminders=None, stream="https://s/x"):
    async with maker() as s:
        e = Event(
            tenant_id=tenant_id,
            name="Webinar",
            event_type=EventType.WEBINAR,
            config={"capacity": capacity, "reminders": reminders or [], "stream_url": stream},
            starts_at=datetime(2026, 7, 1, 17, tzinfo=timezone.utc),
            ends_at=datetime(2026, 7, 1, 18, tzinfo=timezone.utc),
        )
        s.add(e)
        await s.commit()
        await s.refresh(e)
        return e.id


async def _user(maker, tenant_id, email):
    async with maker() as s:
        u = User(email=email, role=Role.USER, tenant_id=tenant_id)
        s.add(u)
        await s.commit()
        await s.refresh(u)
        return u


async def test_register_overflow_and_promotion(seeded):
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    eid = await _webinar(maker, t1, capacity=1)
    u1 = await _user(maker, t1, "a@x.com")
    u2 = await _user(maker, t1, "b@x.com")
    async with maker() as s:
        svc = WebinarService(s)
        r1 = await svc.register(eid, u1, t1)
        r2 = await svc.register(eid, u2, t1)
        assert r1.status is RegistrationStatus.REGISTERED
        assert r2.status is RegistrationStatus.WAITLISTED
        # cancelling the registered seat promotes the waitlisted user
        await svc.cancel(eid, u1, t1)
        st = await svc.status(eid, u2, t1)
        assert st.my_state is RegistrationStatus.REGISTERED
        assert st.registered_count == 1
        assert st.waitlisted_count == 0


async def test_capacity_zero_unlimited(seeded):
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    eid = await _webinar(maker, t1, capacity=0)
    u1 = await _user(maker, t1, "a@x.com")
    async with maker() as s:
        svc = WebinarService(s)
        r = await svc.register(eid, u1, t1)
        st = await svc.status(eid, u1, t1)
    assert r.status is RegistrationStatus.REGISTERED
    assert st.seats_left is None


async def test_bad_capacity_value_treated_as_unlimited(seeded):
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    async with maker() as s:
        e = Event(
            tenant_id=t1, name="W", event_type=EventType.WEBINAR,
            config={"capacity": "lots"},  # non-numeric → unlimited
            starts_at=datetime(2026, 7, 1, 17, tzinfo=timezone.utc),
            ends_at=datetime(2026, 7, 1, 18, tzinfo=timezone.utc),
        )
        s.add(e)
        await s.commit()
        await s.refresh(e)
        eid = e.id
    u1 = await _user(maker, t1, "a@x.com")
    async with maker() as s:
        svc = WebinarService(s)
        st = await svc.status(eid, u1, t1)
    assert st.capacity == 0
    assert st.seats_left is None


async def test_cancel_without_registration_raises(seeded):
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    eid = await _webinar(maker, t1)
    u1 = await _user(maker, t1, "a@x.com")
    async with maker() as s:
        svc = WebinarService(s)
        with pytest.raises(NotFoundError):
            await svc.cancel(eid, u1, t1)


async def test_cancel_waitlisted_does_not_promote(seeded):
    """Cancelling a WAITLISTED row must not promote anyone (no seat freed)."""
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    eid = await _webinar(maker, t1, capacity=1)
    u1 = await _user(maker, t1, "a@x.com")
    u2 = await _user(maker, t1, "b@x.com")
    u3 = await _user(maker, t1, "c@x.com")
    async with maker() as s:
        svc = WebinarService(s)
        await svc.register(eid, u1, t1)  # registered
        await svc.register(eid, u2, t1)  # waitlisted
        await svc.register(eid, u3, t1)  # waitlisted
        # u2 (waitlisted) cancels -> u3 stays waitlisted, u1 stays registered
        await svc.cancel(eid, u2, t1)
        st = await svc.status(eid, u3, t1)
    assert st.registered_count == 1
    assert st.waitlisted_count == 1
    assert st.my_state is RegistrationStatus.WAITLISTED


async def test_waitlist_ordering_and_reminders(seeded):
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    eid = await _webinar(maker, t1, capacity=0, reminders=["1h", "24h"])
    u1 = await _user(maker, t1, "a@x.com")
    u2 = await _user(maker, t1, "b@x.com")
    async with maker() as s:
        s.add_all([
            EventRegistration(event_id=eid, user_id=u1.id, status=RegistrationStatus.WAITLISTED,
                              created_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
                              updated_at=datetime(2026, 6, 1, tzinfo=timezone.utc)),
            EventRegistration(event_id=eid, user_id=u2.id, status=RegistrationStatus.WAITLISTED,
                              created_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
                              updated_at=datetime(2026, 6, 2, tzinfo=timezone.utc)),
        ])
        await s.commit()
    async with maker() as s:
        svc = WebinarService(s)
        wl = await svc.waitlist(eid, t1)
        rem = await svc.reminders(eid, t1)
    assert [w.position for w in wl] == [1, 2]
    assert wl[0].email == "a@x.com"
    # reminders sorted ascending by send time → 24h-before first
    assert [r.offset for r in rem] == ["24h", "1h"]


async def test_status_none_when_not_registered(seeded):
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    eid = await _webinar(maker, t1)
    u1 = await _user(maker, t1, "a@x.com")
    async with maker() as s:
        svc = WebinarService(s)
        st = await svc.status(eid, u1, t1)
    assert st.my_state is None


async def test_register_idempotent_when_already_active(seeded):
    """Re-registering while already REGISTERED returns the same row unchanged
    (the idempotent early-return), without double-counting."""
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    eid = await _webinar(maker, t1, capacity=2)
    u1 = await _user(maker, t1, "a@x.com")
    async with maker() as s:
        svc = WebinarService(s)
        first = await svc.register(eid, u1, t1)
        again = await svc.register(eid, u1, t1)
        assert again.id == first.id
        assert again.status is RegistrationStatus.REGISTERED
        st = await svc.status(eid, u1, t1)
        assert st.registered_count == 1


async def test_reregister_after_cancel_reactivates_row(seeded):
    """Re-registering a previously CANCELLED row flips it back (the else branch),
    not a duplicate, and respects capacity at that moment."""
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    eid = await _webinar(maker, t1, capacity=2)
    u1 = await _user(maker, t1, "a@x.com")
    async with maker() as s:
        svc = WebinarService(s)
        await svc.register(eid, u1, t1)
        await svc.cancel(eid, u1, t1)
        again = await svc.register(eid, u1, t1)
        assert again.status is RegistrationStatus.REGISTERED
    async with maker() as s:
        from sqlalchemy import func, select
        count = await s.scalar(
            select(func.count())
            .select_from(EventRegistration)
            .where(EventRegistration.event_id == eid, EventRegistration.user_id == u1.id)
        )
    assert count == 1  # reactivated in place, not duplicated


async def test_reregister_after_cancel_waitlists_when_full(seeded):
    """If the webinar filled up while a user was cancelled, re-registering puts
    them on the waitlist (capacity re-checked on the else branch)."""
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    eid = await _webinar(maker, t1, capacity=1)
    u1 = await _user(maker, t1, "a@x.com")
    u2 = await _user(maker, t1, "b@x.com")
    async with maker() as s:
        svc = WebinarService(s)
        await svc.register(eid, u1, t1)   # registered (seat taken)
        await svc.cancel(eid, u1, t1)     # frees seat (no one waiting)
        await svc.register(eid, u2, t1)   # u2 takes the seat
        again = await svc.register(eid, u1, t1)  # u1 returns -> waitlisted
        assert again.status is RegistrationStatus.WAITLISTED
