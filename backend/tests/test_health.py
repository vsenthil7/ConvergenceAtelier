"""Health endpoint — functional and negative coverage."""
from __future__ import annotations

import httpx
import pytest

from app.main import create_app


@pytest.fixture
def client():
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def test_health_ok(client):
    """Functional: health returns ok with required fields."""
    async with client as c:
        resp = await c.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "Convergence Atelier"
    assert body["mode"] in {"mock", "live"}
    assert "version" in body
    # time must be ISO and timezone-aware (carries a UTC offset)
    assert "T" in body["time"]
    assert body["time"].endswith("+00:00")


async def test_unknown_route_404(client):
    """Negative: unknown route returns 404, not 500."""
    async with client as c:
        resp = await c.get("/api/does-not-exist")
    assert resp.status_code == 404


async def test_health_rejects_post(client):
    """Negative: wrong method returns 405."""
    async with client as c:
        resp = await c.post("/api/health")
    assert resp.status_code == 405
