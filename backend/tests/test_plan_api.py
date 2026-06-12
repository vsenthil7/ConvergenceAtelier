"""Plan endpoint API tests (S7.6): type-aware draft, auth, tenant scope."""
from __future__ import annotations

from datetime import datetime, timezone

from app.models.event import Event, EventType
from app.models.identity import Role
from tests.conftest import bearer


async def _typed_event(maker, tenant_id, event_type):
    async with maker() as s:
        e = Event(
            tenant_id=tenant_id,
            name=f"{event_type.value} event",
            event_type=event_type,
            starts_at=datetime(2026, 7, 1, 9, tzinfo=timezone.utc),
            ends_at=datetime(2026, 7, 3, 17, tzinfo=timezone.utc),
        )
        s.add(e)
        await s.commit()
        await s.refresh(e)
        return e.id


async def test_plan_endpoint_returns_hackathon_schedule(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await _typed_event(maker, ids["t1"], EventType.HACKATHON)
    async with make_client(maker, bearer(ids["u1"], Role.USER, ids["t1"])) as c:
        resp = await c.post(
            f"/api/discovery/events/{eid}/plan", json={"theme": "judging"}
        )
    assert resp.status_code == 200
    rows = resp.json()
    assert [r["key"] for r in rows] == [
        "registration", "kickoff", "build", "submit", "judging", "awards"
    ]
    # each item carries a target time + a 0..1 relevance
    assert all("target_at" in r and 0.0 <= r["relevance"] <= 1.0 for r in rows)


async def test_plan_endpoint_webinar_promo(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await _typed_event(maker, ids["t1"], EventType.WEBINAR)
    async with make_client(maker, bearer(ids["a1"], Role.TENANT_ADMIN, ids["t1"])) as c:
        resp = await c.post(f"/api/discovery/events/{eid}/plan", json={"theme": "promo"})
    rows = resp.json()
    assert rows[0]["key"] == "announce"
    assert rows[-1]["key"] == "followup"


async def test_plan_endpoint_default_theme_optional(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await _typed_event(maker, ids["t1"], EventType.CONFERENCE)
    async with make_client(maker, bearer(ids["u1"], Role.USER, ids["t1"])) as c:
        # no theme key at all -> empty theme default
        resp = await c.post(f"/api/discovery/events/{eid}/plan", json={})
    assert resp.status_code == 200
    assert [r["key"] for r in resp.json()] == ["cfp", "schedule", "runofshow", "wrap"]


async def test_plan_endpoint_requires_auth(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await _typed_event(maker, ids["t1"], EventType.HACKATHON)
    async with make_client(maker) as c:
        resp = await c.post(f"/api/discovery/events/{eid}/plan", json={"theme": "x"})
    assert resp.status_code == 401


async def test_plan_endpoint_tenant_isolation(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    other = await _typed_event(maker, ids["t2"], EventType.HACKATHON)
    async with make_client(maker, bearer(ids["u1"], Role.USER, ids["t1"])) as c:
        resp = await c.post(f"/api/discovery/events/{other}/plan", json={"theme": "x"})
    assert resp.status_code == 404


async def test_plan_endpoint_super_admin_spans_tenants(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await _typed_event(maker, ids["t2"], EventType.WORKSHOP)
    async with make_client(maker, bearer(ids["sa"], Role.SUPER_ADMIN, None)) as c:
        resp = await c.post(f"/api/discovery/events/{eid}/plan", json={"theme": "materials"})
    assert resp.status_code == 200
    assert resp.json()[0]["key"] == "prereqs"
