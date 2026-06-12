"""Event-links module API tests (S7.5): link/unlink, list, combined catalog, RBAC."""
from __future__ import annotations

from datetime import datetime, timezone

from app.models.event import Event
from app.models.identity import Role
from tests.conftest import bearer, make_event, make_session


def _admin1(ids):
    return bearer(ids["a1"], Role.TENANT_ADMIN, ids["t1"])


def _user1(ids):
    return bearer(ids["u1"], Role.USER, ids["t1"])


async def test_link_and_list(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    e1 = await make_event(maker, ids["t1"], "Flagship")
    e2 = await make_event(maker, ids["t1"], "Online")
    async with make_client(maker, _admin1(ids)) as c:
        linked = await c.post(f"/api/events/{e1}/links", json={"other_event_id": e2})
        assert linked.status_code == 201
        assert [e["id"] for e in linked.json()] == [e2]
        # symmetric: e2 lists e1 too
        back = await c.get(f"/api/events/{e2}/links")
    assert [e["id"] for e in back.json()] == [e1]


async def test_unlink(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    e1 = await make_event(maker, ids["t1"], "A")
    e2 = await make_event(maker, ids["t1"], "B")
    async with make_client(maker, _admin1(ids)) as c:
        await c.post(f"/api/events/{e1}/links", json={"other_event_id": e2})
        removed = await c.request("DELETE", f"/api/events/{e1}/links/{e2}")
        assert removed.status_code == 200
        assert removed.json() == []
        assert (await c.get(f"/api/events/{e1}/links")).json() == []


async def test_self_link_rejected(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    e1 = await make_event(maker, ids["t1"], "A")
    async with make_client(maker, _admin1(ids)) as c:
        resp = await c.post(f"/api/events/{e1}/links", json={"other_event_id": e1})
    assert resp.status_code == 409


async def test_duplicate_link_conflict(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    e1 = await make_event(maker, ids["t1"], "A")
    e2 = await make_event(maker, ids["t1"], "B")
    async with make_client(maker, _admin1(ids)) as c:
        await c.post(f"/api/events/{e1}/links", json={"other_event_id": e2})
        # linking the reverse direction is the same unordered pair -> conflict
        again = await c.post(f"/api/events/{e2}/links", json={"other_event_id": e1})
    assert again.status_code == 409


async def test_user_cannot_link_403(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    e1 = await make_event(maker, ids["t1"], "A")
    e2 = await make_event(maker, ids["t1"], "B")
    async with make_client(maker, _user1(ids)) as c:
        resp = await c.post(f"/api/events/{e1}/links", json={"other_event_id": e2})
    assert resp.status_code == 403


async def test_link_cross_tenant_404(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    e1 = await make_event(maker, ids["t1"], "Mine")
    other = await make_event(maker, ids["t2"], "Theirs")
    async with make_client(maker, _admin1(ids)) as c:
        resp = await c.post(f"/api/events/{e1}/links", json={"other_event_id": other})
    assert resp.status_code == 404


async def test_unlink_missing_404(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    e1 = await make_event(maker, ids["t1"], "A")
    e2 = await make_event(maker, ids["t1"], "B")
    async with make_client(maker, _admin1(ids)) as c:
        resp = await c.request("DELETE", f"/api/events/{e1}/links/{e2}")
    assert resp.status_code == 404


async def test_combined_catalog_spans_linked_events(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    e1 = await make_event(maker, ids["t1"], "Flagship")
    e2 = await make_event(maker, ids["t1"], "Online")
    await make_session(maker, e1, title="In-person Talk")
    await make_session(maker, e2, title="Online Talk")
    async with make_client(maker, _admin1(ids)) as c:
        await c.post(f"/api/events/{e1}/links", json={"other_event_id": e2})
        catalog = await c.get(f"/api/events/{e1}/catalog")
    rows = catalog.json()
    titles = {r["title"] for r in rows}
    assert titles == {"In-person Talk", "Online Talk"}
    # each row is tagged with its source event name
    by_title = {r["title"]: r["event_name"] for r in rows}
    assert by_title["In-person Talk"] == "Flagship"
    assert by_title["Online Talk"] == "Online"


async def test_catalog_without_links_is_own_sessions(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    e1 = await make_event(maker, ids["t1"], "Solo")
    await make_session(maker, e1, title="Only Talk")
    async with make_client(maker, _admin1(ids)) as c:
        catalog = await c.get(f"/api/events/{e1}/catalog")
    assert [r["title"] for r in catalog.json()] == ["Only Talk"]


async def test_attendee_can_read_links_and_catalog(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    e1 = await make_event(maker, ids["t1"], "A")
    e2 = await make_event(maker, ids["t1"], "B")
    async with make_client(maker, _admin1(ids)) as c:
        await c.post(f"/api/events/{e1}/links", json={"other_event_id": e2})
    async with make_client(maker, _user1(ids)) as c:
        assert (await c.get(f"/api/events/{e1}/links")).status_code == 200
        assert (await c.get(f"/api/events/{e1}/catalog")).status_code == 200


async def test_links_require_auth(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    e1 = await make_event(maker, ids["t1"], "A")
    async with make_client(maker) as c:
        assert (await c.get(f"/api/events/{e1}/links")).status_code == 401
