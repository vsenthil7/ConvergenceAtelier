"""Event + agenda API — functional and negative coverage."""
from __future__ import annotations

from tests.conftest import event_payload, session_payload


# ---------- functional ----------

async def test_list_empty(client):
    resp = await client.get("/api/events")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_create_and_get_event(client):
    resp = await client.post("/api/events", json=event_payload())
    assert resp.status_code == 201
    created = resp.json()
    assert created["name"] == "React Summit"
    assert created["sessions"] == []

    got = await client.get(f"/api/events/{created['id']}")
    assert got.status_code == 200
    assert got.json()["id"] == created["id"]


async def test_list_after_create(client):
    await client.post("/api/events", json=event_payload())
    resp = await client.get("/api/events")
    assert len(resp.json()) == 1


async def test_update_event(client):
    created = (await client.post("/api/events", json=event_payload())).json()
    resp = await client.patch(
        f"/api/events/{created['id']}", json={"name": "JSNation"}
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "JSNation"


async def test_delete_event(client):
    created = (await client.post("/api/events", json=event_payload())).json()
    resp = await client.delete(f"/api/events/{created['id']}")
    assert resp.status_code == 204
    assert (await client.get(f"/api/events/{created['id']}")).status_code == 404


async def test_add_session_to_event(client):
    created = (await client.post("/api/events", json=event_payload())).json()
    resp = await client.post(
        f"/api/events/{created['id']}/sessions", json=session_payload()
    )
    assert resp.status_code == 201
    assert resp.json()["title"] == "Keynote"

    got = await client.get(f"/api/events/{created['id']}")
    assert len(got.json()["sessions"]) == 1


# ---------- negative ----------

async def test_get_missing_event_404(client):
    assert (await client.get("/api/events/nope")).status_code == 404


async def test_update_missing_event_404(client):
    resp = await client.patch("/api/events/nope", json={"name": "X"})
    assert resp.status_code == 404


async def test_delete_missing_event_404(client):
    assert (await client.delete("/api/events/nope")).status_code == 404


async def test_add_session_missing_event_404(client):
    resp = await client.post("/api/events/nope/sessions", json=session_payload())
    assert resp.status_code == 404


async def test_create_event_end_before_start_422(client):
    bad = event_payload(
        starts_at="2026-06-12T17:00:00+00:00", ends_at="2026-06-11T09:00:00+00:00"
    )
    assert (await client.post("/api/events", json=bad)).status_code == 422


async def test_create_event_naive_datetime_422(client):
    bad = event_payload(starts_at="2026-06-11T09:00:00", ends_at="2026-06-12T17:00:00")
    assert (await client.post("/api/events", json=bad)).status_code == 422


async def test_create_event_blank_name_422(client):
    assert (await client.post("/api/events", json=event_payload(name=""))).status_code == 422


async def test_update_event_end_before_start_422(client):
    created = (await client.post("/api/events", json=event_payload())).json()
    resp = await client.patch(
        f"/api/events/{created['id']}",
        json={
            "starts_at": "2026-06-12T17:00:00+00:00",
            "ends_at": "2026-06-11T09:00:00+00:00",
        },
    )
    assert resp.status_code == 422


async def test_update_event_naive_start_422(client):
    created = (await client.post("/api/events", json=event_payload())).json()
    resp = await client.patch(
        f"/api/events/{created['id']}", json={"starts_at": "2026-06-11T09:00:00"}
    )
    assert resp.status_code == 422


async def test_update_event_naive_end_422(client):
    created = (await client.post("/api/events", json=event_payload())).json()
    resp = await client.patch(
        f"/api/events/{created['id']}", json={"ends_at": "2026-06-12T17:00:00"}
    )
    assert resp.status_code == 422


async def test_session_end_before_start_422(client):
    created = (await client.post("/api/events", json=event_payload())).json()
    bad = session_payload(
        starts_at="2026-06-11T11:00:00+00:00", ends_at="2026-06-11T10:00:00+00:00"
    )
    resp = await client.post(f"/api/events/{created['id']}/sessions", json=bad)
    assert resp.status_code == 422


async def test_session_naive_datetime_422(client):
    created = (await client.post("/api/events", json=event_payload())).json()
    bad = session_payload(starts_at="2026-06-11T10:00:00", ends_at="2026-06-11T11:00:00")
    resp = await client.post(f"/api/events/{created['id']}/sessions", json=bad)
    assert resp.status_code == 422
