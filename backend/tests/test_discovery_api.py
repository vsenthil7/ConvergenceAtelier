"""Discovery API tests: auth-gated, tenant-scoped, all roles, negative paths."""
from __future__ import annotations

from app.models.identity import Role
from tests.conftest import bearer, make_event, make_session


async def _agenda(maker, tenant_id):
    event_id = await make_event(maker, tenant_id, name="DevConf")
    rid = await make_session(maker, event_id, title="React hooks deep dive", track="Frontend", speaker="Ada")
    rid2 = await make_session(maker, event_id, title="Advanced React hooks and state", track="Frontend", speaker="Lin")
    bid = await make_session(maker, event_id, title="Sourdough bread baking", track="Lifestyle", speaker="Sam")
    return {"react": rid, "react2": rid2, "bread": bid}


async def test_similar_requires_auth(seeded, make_client):
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    ids = await _agenda(maker, t1)
    async with make_client(maker) as client:  # no auth header
        resp = await client.get(f"/api/discovery/sessions/{ids['react']}/similar")
    assert resp.status_code == 401


async def test_similar_sessions_ranks_related(seeded, make_client):
    maker = seeded["maker"]
    t1, u1 = seeded["ids"]["t1"], seeded["ids"]["u1"]
    ids = await _agenda(maker, t1)
    auth = bearer(u1, Role.USER, t1)  # attendee can use discovery
    async with make_client(maker, auth) as client:
        resp = await client.get(f"/api/discovery/sessions/{ids['react']}/similar?limit=5")
    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["session"]["id"] == ids["react2"]
    assert 0.0 <= body[0]["score"] <= 1.0


async def test_similar_unknown_session_404(seeded, make_client):
    maker, t1, u1 = seeded["maker"], seeded["ids"]["t1"], seeded["ids"]["u1"]
    await _agenda(maker, t1)
    auth = bearer(u1, Role.USER, t1)
    async with make_client(maker, auth) as client:
        resp = await client.get("/api/discovery/sessions/missing/similar")
    assert resp.status_code == 404


async def test_recommend_for_interests(seeded, make_client):
    maker, t1, u1 = seeded["maker"], seeded["ids"]["t1"], seeded["ids"]["u1"]
    ids = await _agenda(maker, t1)
    auth = bearer(u1, Role.USER, t1)
    async with make_client(maker, auth) as client:
        resp = await client.post(
            "/api/discovery/recommend",
            json={"interests": "frontend react hooks", "limit": 2},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    top_ids = {r["session"]["id"] for r in body}
    assert ids["react"] in top_ids or ids["react2"] in top_ids


async def test_recommend_validation_rejects_empty_interests(seeded, make_client):
    maker, t1, u1 = seeded["maker"], seeded["ids"]["t1"], seeded["ids"]["u1"]
    await _agenda(maker, t1)
    auth = bearer(u1, Role.USER, t1)
    async with make_client(maker, auth) as client:
        resp = await client.post("/api/discovery/recommend", json={"interests": ""})
    assert resp.status_code == 422


async def test_tenant_cannot_see_other_tenant_sessions(seeded, make_client):
    maker = seeded["maker"]
    t1, t2 = seeded["ids"]["t1"], seeded["ids"]["t2"]
    u1 = seeded["ids"]["u1"]
    await _agenda(maker, t1)
    e2 = await make_event(maker, t2, name="OtherConf")
    secret = await make_session(maker, e2, title="Secret t2 talk", speaker="Zed")
    auth = bearer(u1, Role.USER, t1)
    async with make_client(maker, auth) as client:
        resp = await client.post(
            "/api/discovery/recommend", json={"interests": "talk", "limit": 50}
        )
    assert resp.status_code == 200
    ids = {r["session"]["id"] for r in resp.json()}
    assert secret not in ids


async def test_match_attendees_endpoint(seeded, make_client):
    maker, t1, a1 = seeded["maker"], seeded["ids"]["t1"], seeded["ids"]["a1"]
    auth = bearer(a1, Role.TENANT_ADMIN, t1)
    async with make_client(maker, auth) as client:
        resp = await client.post(
            "/api/discovery/match",
            json={
                "attendees": [
                    {"id": "1", "name": "Ann", "interests": "react frontend hooks"},
                    {"id": "2", "name": "Bob", "interests": "react state frontend"},
                    {"id": "3", "name": "Cy", "interests": "sourdough bread"},
                ],
                "limit": 5,
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    top = body[0]
    assert {top["a"]["id"], top["b"]["id"]} == {"1", "2"}


async def test_match_requires_two_attendees(seeded, make_client):
    maker, t1, a1 = seeded["maker"], seeded["ids"]["t1"], seeded["ids"]["a1"]
    auth = bearer(a1, Role.TENANT_ADMIN, t1)
    async with make_client(maker, auth) as client:
        resp = await client.post(
            "/api/discovery/match",
            json={"attendees": [{"id": "1", "name": "Solo", "interests": "x"}]},
        )
    assert resp.status_code == 422


async def test_super_admin_spans_all_tenants(seeded, make_client):
    maker = seeded["maker"]
    t1, t2, sa = seeded["ids"]["t1"], seeded["ids"]["t2"], seeded["ids"]["sa"]
    await _agenda(maker, t1)
    e2 = await make_event(maker, t2, name="OtherConf")
    await make_session(maker, e2, title="Tenant 2 talk", speaker="Zed")
    auth = bearer(sa, Role.SUPER_ADMIN, None)
    async with make_client(maker, auth) as client:
        resp = await client.post(
            "/api/discovery/recommend", json={"interests": "talk", "limit": 50}
        )
    assert resp.status_code == 200
    assert len(resp.json()) == 4  # 3 in t1 + 1 in t2


async def test_super_admin_similar_sessions(seeded, make_client):
    """Super-admin hits the GET /similar path with cross-tenant scope (None)."""
    maker = seeded["maker"]
    t1, sa = seeded["ids"]["t1"], seeded["ids"]["sa"]
    ids = await _agenda(maker, t1)
    auth = bearer(sa, Role.SUPER_ADMIN, None)
    async with make_client(maker, auth) as client:
        resp = await client.get(f"/api/discovery/sessions/{ids['react']}/similar")
    assert resp.status_code == 200
    assert resp.json()[0]["session"]["id"] == ids["react2"]


async def test_agenda_draft_endpoint(seeded, make_client):
    """Agenda draft returns an ordered, theme-ranked running order."""
    maker = seeded["maker"]
    t1, a1 = seeded["ids"]["t1"], seeded["ids"]["a1"]
    # Build an event with a known id by creating it then reading discovery later.
    event_id = await make_event(maker, t1, name="DevConf")
    await make_session(maker, event_id, title="React hooks performance", track="Frontend", speaker="Ada")
    await make_session(maker, event_id, title="Sourdough baking", track="Lifestyle", speaker="Sam")
    auth = bearer(a1, Role.TENANT_ADMIN, t1)
    async with make_client(maker, auth) as client:
        resp = await client.post(
            f"/api/discovery/events/{event_id}/agenda-draft",
            json={"theme": "react frontend"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert [slot["order"] for slot in body] == [0, 1]
    assert body[0]["track"] == "Frontend"  # on-theme track opens
    assert 0.0 <= body[0]["relevance"] <= 1.0


async def test_agenda_draft_unknown_event_404(seeded, make_client):
    maker, t1, a1 = seeded["maker"], seeded["ids"]["t1"], seeded["ids"]["a1"]
    auth = bearer(a1, Role.TENANT_ADMIN, t1)
    async with make_client(maker, auth) as client:
        resp = await client.post(
            "/api/discovery/events/missing/agenda-draft", json={"theme": "x"}
        )
    assert resp.status_code == 404


async def test_agenda_draft_requires_theme(seeded, make_client):
    maker, t1, a1 = seeded["maker"], seeded["ids"]["t1"], seeded["ids"]["a1"]
    event_id = await make_event(maker, t1, name="DevConf")
    auth = bearer(a1, Role.TENANT_ADMIN, t1)
    async with make_client(maker, auth) as client:
        resp = await client.post(
            f"/api/discovery/events/{event_id}/agenda-draft", json={"theme": ""}
        )
    assert resp.status_code == 422
