"""Webinar module API tests (S7.4): capacity, waitlist, promotion, reminders."""
from __future__ import annotations

from datetime import datetime, timezone

from app.models.event import Event, EventType
from app.models.identity import Role, User
from app.models.registration import EventRegistration, RegistrationStatus
from tests.conftest import bearer


async def _webinar(maker, tenant_id, capacity=2, reminders=None, stream="https://s/x"):
    async with maker() as s:
        e = Event(
            tenant_id=tenant_id,
            name="Webinar",
            event_type=EventType.WEBINAR,
            config={"capacity": capacity, "reminders": reminders or ["24h", "1h"], "stream_url": stream},
            starts_at=datetime(2026, 7, 1, 17, tzinfo=timezone.utc),
            ends_at=datetime(2026, 7, 1, 18, tzinfo=timezone.utc),
        )
        s.add(e)
        await s.commit()
        await s.refresh(e)
        return e.id


async def _extra_user(maker, tenant_id, email):
    async with maker() as s:
        u = User(email=email, role=Role.USER, tenant_id=tenant_id)
        s.add(u)
        await s.commit()
        await s.refresh(u)
        return u.id


async def test_register_fills_seat_then_status(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await _webinar(maker, ids["t1"], capacity=2)
    async with make_client(maker, bearer(ids["u1"], Role.USER, ids["t1"])) as c:
        reg = await c.post(f"/api/events/{eid}/webinar/register")
        assert reg.status_code == 201
        assert reg.json()["status"] == "registered"
        st = await c.get(f"/api/events/{eid}/webinar/status")
    body = st.json()
    assert body["capacity"] == 2
    assert body["registered_count"] == 1
    assert body["seats_left"] == 1
    assert body["my_state"] == "registered"
    assert body["stream_url"] == "https://s/x"


async def test_capacity_overflow_waitlists(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await _webinar(maker, ids["t1"], capacity=1)
    u2 = await _extra_user(maker, ids["t1"], "w2@x.com")
    async with make_client(maker, bearer(ids["u1"], Role.USER, ids["t1"])) as c:
        first = await c.post(f"/api/events/{eid}/webinar/register")
        assert first.json()["status"] == "registered"
    async with make_client(maker, bearer(u2, Role.USER, ids["t1"])) as c:
        second = await c.post(f"/api/events/{eid}/webinar/register")
        assert second.json()["status"] == "waitlisted"
        st = await c.get(f"/api/events/{eid}/webinar/status")
    assert st.json()["waitlisted_count"] == 1
    assert st.json()["seats_left"] == 0


async def test_cancel_promotes_waitlist_head(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await _webinar(maker, ids["t1"], capacity=1)
    u2 = await _extra_user(maker, ids["t1"], "w2@x.com")
    async with make_client(maker, bearer(ids["u1"], Role.USER, ids["t1"])) as c:
        await c.post(f"/api/events/{eid}/webinar/register")  # registered
    async with make_client(maker, bearer(u2, Role.USER, ids["t1"])) as c:
        await c.post(f"/api/events/{eid}/webinar/register")  # waitlisted
    # u1 cancels -> u2 should be auto-promoted
    async with make_client(maker, bearer(ids["u1"], Role.USER, ids["t1"])) as c:
        await c.request("DELETE", f"/api/events/{eid}/webinar/register")
    async with make_client(maker, bearer(u2, Role.USER, ids["t1"])) as c:
        st = await c.get(f"/api/events/{eid}/webinar/status")
    assert st.json()["my_state"] == "registered"
    assert st.json()["registered_count"] == 1
    assert st.json()["waitlisted_count"] == 0


async def test_unlimited_capacity_never_waitlists(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await _webinar(maker, ids["t1"], capacity=0)
    async with make_client(maker, bearer(ids["u1"], Role.USER, ids["t1"])) as c:
        reg = await c.post(f"/api/events/{eid}/webinar/register")
        st = await c.get(f"/api/events/{eid}/webinar/status")
    assert reg.json()["status"] == "registered"
    assert st.json()["seats_left"] is None  # unlimited


async def test_register_is_idempotent(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await _webinar(maker, ids["t1"], capacity=2)
    async with make_client(maker, bearer(ids["u1"], Role.USER, ids["t1"])) as c:
        await c.post(f"/api/events/{eid}/webinar/register")
        again = await c.post(f"/api/events/{eid}/webinar/register")
        st = await c.get(f"/api/events/{eid}/webinar/status")
    assert again.json()["status"] == "registered"
    assert st.json()["registered_count"] == 1  # not double-counted


async def test_cancel_without_registration_404(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await _webinar(maker, ids["t1"])
    async with make_client(maker, bearer(ids["u1"], Role.USER, ids["t1"])) as c:
        resp = await c.request("DELETE", f"/api/events/{eid}/webinar/register")
    assert resp.status_code == 404


async def test_admin_sees_ordered_waitlist(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await _webinar(maker, ids["t1"], capacity=0)
    # directly seed two waitlisted rows with known order
    u2 = await _extra_user(maker, ids["t1"], "w2@x.com")
    async with maker() as s:
        s.add_all([
            EventRegistration(event_id=eid, user_id=ids["u1"], status=RegistrationStatus.WAITLISTED,
                              created_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
                              updated_at=datetime(2026, 6, 1, tzinfo=timezone.utc)),
            EventRegistration(event_id=eid, user_id=u2, status=RegistrationStatus.WAITLISTED,
                              created_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
                              updated_at=datetime(2026, 6, 2, tzinfo=timezone.utc)),
        ])
        await s.commit()
    async with make_client(maker, bearer(ids["a1"], Role.TENANT_ADMIN, ids["t1"])) as c:
        wl = await c.get(f"/api/events/{eid}/webinar/waitlist")
    rows = wl.json()
    assert [r["position"] for r in rows] == [1, 2]
    assert rows[0]["user_id"] == ids["u1"]  # earliest created_at first


async def test_attendee_cannot_see_waitlist_403(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await _webinar(maker, ids["t1"])
    async with make_client(maker, bearer(ids["u1"], Role.USER, ids["t1"])) as c:
        resp = await c.get(f"/api/events/{eid}/webinar/waitlist")
    assert resp.status_code == 403


async def test_reminders_computed_from_config(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await _webinar(maker, ids["t1"], reminders=["1h", "24h", "bogus"])
    async with make_client(maker, bearer(ids["u1"], Role.USER, ids["t1"])) as c:
        rem = await c.get(f"/api/events/{eid}/webinar/reminders")
    rows = rem.json()
    # bogus token dropped; sorted ascending by send time (24h before, then 1h before)
    assert [r["offset"] for r in rows] == ["24h", "1h"]
    assert rows[0]["send_at"] < rows[1]["send_at"]


async def test_status_requires_auth(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await _webinar(maker, ids["t1"])
    async with make_client(maker) as c:
        assert (await c.get(f"/api/events/{eid}/webinar/status")).status_code == 401


async def test_webinar_tenant_isolation(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    other = await _webinar(maker, ids["t2"])
    async with make_client(maker, bearer(ids["u1"], Role.USER, ids["t1"])) as c:
        assert (await c.get(f"/api/events/{other}/webinar/status")).status_code == 404
