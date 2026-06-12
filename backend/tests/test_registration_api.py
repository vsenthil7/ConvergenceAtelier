"""Registration + participation API tests (auth-gated, RBAC, tenant-scoped)."""
from __future__ import annotations

from app.models.identity import Role
from tests.conftest import bearer, make_event


async def test_register_requires_auth(seeded, make_client):
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    event_id = await make_event(maker, t1, name="Conf")
    async with make_client(maker) as client:
        resp = await client.post(f"/api/events/{event_id}/register")
    assert resp.status_code == 401


async def test_attendee_registers_and_sees_status(seeded, make_client):
    maker, t1, u1 = seeded["maker"], seeded["ids"]["t1"], seeded["ids"]["u1"]
    event_id = await make_event(maker, t1, name="Conf")
    auth = bearer(u1, Role.USER, t1)
    async with make_client(maker, auth) as client:
        reg = await client.post(f"/api/events/{event_id}/register")
        assert reg.status_code == 201
        assert reg.json()["status"] == "registered"
        status = await client.get(f"/api/events/{event_id}/registration")
        assert status.status_code == 200
        assert status.json()["status"] == "registered"


async def test_attendee_cancels(seeded, make_client):
    maker, t1, u1 = seeded["maker"], seeded["ids"]["t1"], seeded["ids"]["u1"]
    event_id = await make_event(maker, t1, name="Conf")
    auth = bearer(u1, Role.USER, t1)
    async with make_client(maker, auth) as client:
        await client.post(f"/api/events/{event_id}/register")
        cancel = await client.request("DELETE", f"/api/events/{event_id}/register")
        assert cancel.status_code == 200
        assert cancel.json()["status"] == "cancelled"


async def test_cancel_without_registration_404(seeded, make_client):
    maker, t1, u1 = seeded["maker"], seeded["ids"]["t1"], seeded["ids"]["u1"]
    event_id = await make_event(maker, t1, name="Conf")
    auth = bearer(u1, Role.USER, t1)
    async with make_client(maker, auth) as client:
        resp = await client.request("DELETE", f"/api/events/{event_id}/register")
    assert resp.status_code == 404


async def test_status_none_when_not_registered(seeded, make_client):
    maker, t1, u1 = seeded["maker"], seeded["ids"]["t1"], seeded["ids"]["u1"]
    event_id = await make_event(maker, t1, name="Conf")
    auth = bearer(u1, Role.USER, t1)
    async with make_client(maker, auth) as client:
        resp = await client.get(f"/api/events/{event_id}/registration")
    assert resp.status_code == 200
    assert resp.json()["status"] is None


async def test_admin_sees_roster(seeded, make_client):
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    a1, u1 = seeded["ids"]["a1"], seeded["ids"]["u1"]
    event_id = await make_event(maker, t1, name="Conf")
    # the attendee registers
    async with make_client(maker, bearer(u1, Role.USER, t1)) as client:
        await client.post(f"/api/events/{event_id}/register")
    # the admin reads the roster
    async with make_client(maker, bearer(a1, Role.TENANT_ADMIN, t1)) as client:
        roster = await client.get(f"/api/events/{event_id}/participants")
    assert roster.status_code == 200
    assert len(roster.json()) == 1


async def test_attendee_cannot_read_roster(seeded, make_client):
    maker, t1, u1 = seeded["maker"], seeded["ids"]["t1"], seeded["ids"]["u1"]
    event_id = await make_event(maker, t1, name="Conf")
    auth = bearer(u1, Role.USER, t1)
    async with make_client(maker, auth) as client:
        resp = await client.get(f"/api/events/{event_id}/participants")
    assert resp.status_code == 403


async def test_register_other_tenant_event_404(seeded, make_client):
    maker = seeded["maker"]
    t1, t2, u1 = seeded["ids"]["t1"], seeded["ids"]["t2"], seeded["ids"]["u1"]
    other_event = await make_event(maker, t2, name="OtherConf")
    auth = bearer(u1, Role.USER, t1)
    async with make_client(maker, auth) as client:
        resp = await client.post(f"/api/events/{other_event}/register")
    assert resp.status_code == 404


# ---------- public self-registration ----------


async def test_public_register_creates_attendee(seeded, make_client):
    maker = seeded["maker"]
    async with make_client(maker) as client:
        resp = await client.post(
            "/api/auth/register",
            json={
                "email": "newbie@x.com",
                "full_name": "New Bie",
                "password": "Secret123!",
                "tenant_slug": "react-org",
            },
        )
    assert resp.status_code == 201
    assert resp.json()["access_token"]


async def test_public_register_unknown_tenant_404(seeded, make_client):
    maker = seeded["maker"]
    async with make_client(maker) as client:
        resp = await client.post(
            "/api/auth/register",
            json={
                "email": "newbie2@x.com",
                "password": "Secret123!",
                "tenant_slug": "does-not-exist",
            },
        )
    assert resp.status_code == 404


async def test_public_register_duplicate_email_conflict(seeded, make_client):
    maker = seeded["maker"]
    payload = {
        "email": "dupe@x.com",
        "password": "Secret123!",
        "tenant_slug": "react-org",
    }
    async with make_client(maker) as client:
        first = await client.post("/api/auth/register", json=payload)
        assert first.status_code == 201
        second = await client.post("/api/auth/register", json=payload)
    assert second.status_code == 409


async def test_public_register_cannot_self_grant_admin(seeded, make_client):
    """Even if a role is smuggled in, the schema ignores it — result is USER."""
    maker = seeded["maker"]
    async with make_client(maker) as client:
        resp = await client.post(
            "/api/auth/register",
            json={
                "email": "sneaky@x.com",
                "password": "Secret123!",
                "tenant_slug": "react-org",
                "role": "super_admin",  # ignored by PublicRegister schema
            },
        )
        assert resp.status_code == 201
        token = resp.json()["access_token"]
        me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["role"] == "user"
