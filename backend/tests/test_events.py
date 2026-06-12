"""Event + agenda API — auth, tenant-scope, functional + negative coverage."""
from __future__ import annotations

from app.models.identity import Role
from tests.conftest import bearer, event_payload, make_event, session_payload


def _admin1(ids):
    return bearer(ids["a1"], Role.TENANT_ADMIN, ids["t1"])


def _admin2(ids):
    return bearer(ids["a2"], Role.TENANT_ADMIN, ids["t2"])


def _super(ids):
    return bearer(ids["sa"], Role.SUPER_ADMIN, None)


def _user1(ids):
    return bearer(ids["u1"], Role.USER, ids["t1"])


# ---------- auth gate ----------

async def test_list_requires_auth(make_client, seeded):
    async with make_client(seeded["maker"]) as c:
        assert (await c.get("/api/events")).status_code == 401


# ---------- functional ----------

async def test_admin_creates_and_lists_event(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    async with make_client(maker, _admin1(ids)) as c:
        created = await c.post("/api/events", json=event_payload())
        assert created.status_code == 201
        listing = await c.get("/api/events")
        assert listing.status_code == 200
        assert len(listing.json()) == 1
        assert listing.json()[0]["name"] == "React Summit"


async def test_get_update_delete_event(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    async with make_client(maker, _admin1(ids)) as c:
        eid = (await c.post("/api/events", json=event_payload())).json()["id"]
        assert (await c.get(f"/api/events/{eid}")).status_code == 200
        patched = await c.patch(f"/api/events/{eid}", json={"name": "JSNation"})
        assert patched.json()["name"] == "JSNation"
        assert (await c.delete(f"/api/events/{eid}")).status_code == 204


async def test_add_session(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    async with make_client(maker, _admin1(ids)) as c:
        eid = (await c.post("/api/events", json=event_payload())).json()["id"]
        resp = await c.post(f"/api/events/{eid}/sessions", json=session_payload())
        assert resp.status_code == 201
        full = await c.get(f"/api/events/{eid}")
        assert len(full.json()["sessions"]) == 1


# ---------- tenant isolation ----------

async def test_tenant_admin_cannot_see_other_tenant_events(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    other = await make_event(maker, ids["t2"], "Vue Conf")
    async with make_client(maker, _admin1(ids)) as c:
        # listing excludes t2's event
        assert (await c.get("/api/events")).json() == []
        # direct get is 404 (out of scope)
        assert (await c.get(f"/api/events/{other}")).status_code == 404


async def test_super_admin_sees_all_tenants(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    await make_event(maker, ids["t1"], "A")
    await make_event(maker, ids["t2"], "B")
    async with make_client(maker, _super(ids)) as c:
        assert len((await c.get("/api/events")).json()) == 2


# ---------- RBAC negatives ----------

async def test_user_cannot_create_event_403(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    async with make_client(maker, _user1(ids)) as c:
        assert (await c.post("/api/events", json=event_payload())).status_code == 403


async def test_user_cannot_update_event_403(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await make_event(maker, ids["t1"])
    async with make_client(maker, _user1(ids)) as c:
        assert (await c.patch(f"/api/events/{eid}", json={"name": "x"})).status_code == 403


async def test_user_cannot_delete_event_403(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await make_event(maker, ids["t1"])
    async with make_client(maker, _user1(ids)) as c:
        assert (await c.delete(f"/api/events/{eid}")).status_code == 403


async def test_user_cannot_add_session_403(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await make_event(maker, ids["t1"])
    async with make_client(maker, _user1(ids)) as c:
        resp = await c.post(f"/api/events/{eid}/sessions", json=session_payload())
        assert resp.status_code == 403


async def test_user_can_read_own_tenant_events(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await make_event(maker, ids["t1"], "Readable")
    async with make_client(maker, _user1(ids)) as c:
        assert (await c.get("/api/events")).status_code == 200
        assert (await c.get(f"/api/events/{eid}")).json()["name"] == "Readable"


async def test_super_admin_without_tenant_cannot_create_403(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    async with make_client(maker, _super(ids)) as c:
        # super-admin has no tenant_id -> create has no tenant context
        assert (await c.post("/api/events", json=event_payload())).status_code == 403


# ---------- validation negatives ----------

async def test_create_event_end_before_start_422(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    bad = event_payload(starts_at="2026-06-12T17:00:00+00:00", ends_at="2026-06-11T09:00:00+00:00")
    async with make_client(maker, _admin1(ids)) as c:
        assert (await c.post("/api/events", json=bad)).status_code == 422


async def test_create_event_naive_422(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    bad = event_payload(starts_at="2026-06-11T09:00:00", ends_at="2026-06-12T17:00:00")
    async with make_client(maker, _admin1(ids)) as c:
        assert (await c.post("/api/events", json=bad)).status_code == 422


async def test_create_event_blank_name_422(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    async with make_client(maker, _admin1(ids)) as c:
        assert (await c.post("/api/events", json=event_payload(name=""))).status_code == 422


async def test_get_missing_event_404(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    async with make_client(maker, _admin1(ids)) as c:
        assert (await c.get("/api/events/nope")).status_code == 404


async def test_update_missing_event_404(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    async with make_client(maker, _admin1(ids)) as c:
        assert (await c.patch("/api/events/nope", json={"name": "x"})).status_code == 404


async def test_delete_missing_event_404(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    async with make_client(maker, _admin1(ids)) as c:
        assert (await c.delete("/api/events/nope")).status_code == 404


async def test_add_session_missing_event_404(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    async with make_client(maker, _admin1(ids)) as c:
        resp = await c.post("/api/events/nope/sessions", json=session_payload())
        assert resp.status_code == 404


async def test_session_end_before_start_422(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await make_event(maker, ids["t1"])
    bad = session_payload(starts_at="2026-06-11T11:00:00+00:00", ends_at="2026-06-11T10:00:00+00:00")
    async with make_client(maker, _admin1(ids)) as c:
        assert (await c.post(f"/api/events/{eid}/sessions", json=bad)).status_code == 422


async def test_update_event_end_before_start_422(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await make_event(maker, ids["t1"])
    async with make_client(maker, _admin1(ids)) as c:
        resp = await c.patch(
            f"/api/events/{eid}",
            json={"starts_at": "2026-06-12T17:00:00+00:00", "ends_at": "2026-06-11T09:00:00+00:00"},
        )
        assert resp.status_code == 422


async def test_update_event_naive_422(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await make_event(maker, ids["t1"])
    async with make_client(maker, _admin1(ids)) as c:
        assert (
            await c.patch(f"/api/events/{eid}", json={"starts_at": "2026-06-11T09:00:00"})
        ).status_code == 422
        assert (
            await c.patch(f"/api/events/{eid}", json={"ends_at": "2026-06-12T17:00:00"})
        ).status_code == 422
