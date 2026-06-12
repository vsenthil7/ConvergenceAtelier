"""Health + readiness — functional and negative coverage."""
from __future__ import annotations

from app.models.identity import Role
from tests.conftest import bearer


async def test_health_ok(make_client, db):
    async with make_client(db) as c:
        resp = await c.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "Convergence Atelier"
    assert body["time"].endswith("+00:00")


async def test_health_rejects_post(make_client, db):
    async with make_client(db) as c:
        resp = await c.post("/api/health")
    assert resp.status_code == 405


async def test_unknown_route_404(make_client, db):
    async with make_client(db) as c:
        resp = await c.get("/api/nope")
    assert resp.status_code == 404


async def test_ready_reports_counts(make_client, seeded):
    maker = seeded["maker"]
    async with make_client(maker) as c:
        resp = await c.get("/api/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["database"] == "ok"
    assert body["tenants"] == 2
    assert body["users"] == 4
    assert body["google_oauth"] is False


async def test_ready_empty_db(make_client, db):
    async with make_client(db) as c:
        resp = await c.get("/api/ready")
    assert resp.status_code == 200
    assert resp.json()["tenants"] == 0
    assert resp.json()["users"] == 0


async def test_ready_called_directly(seeded):
    """Deterministic coverage of the readiness handler body."""
    from app.api.health import ready

    async with seeded["maker"]() as s:
        result = await ready(session=s)
    assert result["status"] == "ready"
    assert result["tenants"] == 2
    assert result["users"] == 4
