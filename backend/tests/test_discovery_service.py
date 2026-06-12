"""Discovery service tests: recommendations, interest matching, attendee matchmaking."""
from __future__ import annotations

import pytest

from app.services.discovery_service import (
    AgendaSlot,
    AttendeeProfile,
    DiscoveryService,
)
from app.services.errors import NotFoundError
from tests.conftest import make_event, make_session


async def _seed_sessions(maker, tenant_id):
    """A small agenda with a clear topical cluster + an outlier."""
    event_id = await make_event(maker, tenant_id, name="DevConf")
    ids = {}
    ids["react"] = await make_session(maker, event_id, title="React hooks deep dive", track="Frontend", speaker="Ada")
    ids["react2"] = await make_session(maker, event_id, title="Advanced React state and hooks", track="Frontend", speaker="Lin")
    ids["bread"] = await make_session(maker, event_id, title="Sourdough bread baking", track="Lifestyle", speaker="Sam")
    return event_id, ids


async def test_recommend_for_session_ranks_related_first(seeded):
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    _event, ids = await _seed_sessions(maker, t1)
    async with maker() as s:
        svc = DiscoveryService(s)
        recs = await svc.recommend_for_session(ids["react"], t1, limit=5)
    # The other React talk should rank above the bread talk.
    assert recs[0].session.id == ids["react2"]
    assert recs[0].score >= recs[-1].score
    # The query session itself is excluded.
    assert all(r.session.id != ids["react"] for r in recs)


async def test_recommend_for_session_respects_limit(seeded):
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    _event, ids = await _seed_sessions(maker, t1)
    async with maker() as s:
        svc = DiscoveryService(s)
        recs = await svc.recommend_for_session(ids["react"], t1, limit=1)
    assert len(recs) == 1


async def test_recommend_for_session_unknown_raises(seeded):
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    await _seed_sessions(maker, t1)
    async with maker() as s:
        svc = DiscoveryService(s)
        with pytest.raises(NotFoundError):
            await svc.recommend_for_session("nope", t1, limit=5)


async def test_recommend_for_interests_matches_topic(seeded):
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    _event, ids = await _seed_sessions(maker, t1)
    async with maker() as s:
        svc = DiscoveryService(s)
        recs = await svc.recommend_for_interests("frontend react hooks", t1, limit=2)
    top_ids = {r.session.id for r in recs}
    assert ids["react"] in top_ids or ids["react2"] in top_ids
    assert recs[0].score >= recs[-1].score


async def test_tenant_scoping_excludes_other_tenant(seeded):
    """A tenant's recommendations never include another tenant's sessions."""
    maker = seeded["maker"]
    t1, t2 = seeded["ids"]["t1"], seeded["ids"]["t2"]
    await _seed_sessions(maker, t1)
    e2 = await make_event(maker, t2, name="OtherConf")
    secret = await make_session(maker, e2, title="Secret tenant-2 talk", speaker="Zed")
    async with maker() as s:
        svc = DiscoveryService(s)
        recs = await svc.recommend_for_interests("anything", t1, limit=50)
    assert all(r.session.id != secret for r in recs)


async def test_super_admin_spans_all_tenants(seeded):
    maker = seeded["maker"]
    t1, t2 = seeded["ids"]["t1"], seeded["ids"]["t2"]
    await _seed_sessions(maker, t1)
    e2 = await make_event(maker, t2, name="OtherConf")
    await make_session(maker, e2, title="Tenant 2 talk", speaker="Zed")
    async with maker() as s:
        svc = DiscoveryService(s)
        recs = await svc.recommend_for_interests("talk", None, limit=50)  # None = span all
    # 3 sessions in t1 + 1 in t2 = 4 total.
    assert len(recs) == 4


def test_match_attendees_pairs_similar_interests():
    svc = DiscoveryService.__new__(DiscoveryService)  # no DB needed for pure match
    from app.core.embedding import default_embedder

    svc.embed = default_embedder()
    people = [
        AttendeeProfile(id="1", name="Ann", interests="react frontend hooks"),
        AttendeeProfile(id="2", name="Bob", interests="react state frontend"),
        AttendeeProfile(id="3", name="Cy", interests="sourdough bread baking"),
    ]
    matches = svc.match_attendees(people, limit=5)
    # Highest-scoring pair should be the two frontend people.
    top = matches[0]
    assert {top.a.id, top.b.id} == {"1", "2"}
    assert top.score >= matches[-1].score


def test_match_attendees_respects_limit():
    svc = DiscoveryService.__new__(DiscoveryService)
    from app.core.embedding import default_embedder

    svc.embed = default_embedder()
    people = [
        AttendeeProfile(id=str(i), name=f"P{i}", interests=f"topic{i}")
        for i in range(5)
    ]  # 10 possible pairs
    matches = svc.match_attendees(people, limit=3)
    assert len(matches) == 3


async def test_injected_embedder_is_used(seeded):
    """A custom embedder replaces the default end-to-end."""
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    _event, ids = await _seed_sessions(maker, t1)
    calls: list[str] = []

    def fake_embedder(text: str) -> list[float]:
        calls.append(text)
        # Constant vector -> all similarities equal, but it must be invoked.
        return [1.0, 0.0, 0.0]

    async with maker() as s:
        svc = DiscoveryService(s, embedder=fake_embedder)
        recs = await svc.recommend_for_interests("frontend", t1, limit=3)
    assert calls, "the injected embedder should have been called"
    assert len(recs) == 3


async def test_draft_agenda_orders_by_theme_and_track(seeded):
    """Most on-theme track opens; talks ordered by relevance within a track."""
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    event_id = await make_event(maker, t1, name="DevConf")
    await make_session(maker, event_id, title="React hooks performance", track="Frontend", speaker="Ada")
    await make_session(maker, event_id, title="React state patterns", track="Frontend", speaker="Lin")
    await make_session(maker, event_id, title="Sourdough bread baking", track="Lifestyle", speaker="Sam")
    async with maker() as s:
        svc = DiscoveryService(s)
        slots = await svc.draft_agenda(event_id, "react frontend performance", t1)
    # Every session placed exactly once, contiguous order indices.
    assert [slot.order for slot in slots] == list(range(len(slots)))
    assert len(slots) == 3
    # The Frontend track (on-theme) should come before Lifestyle.
    first_track = slots[0].track
    assert first_track == "Frontend"
    # All Frontend slots precede the Lifestyle slot.
    tracks_in_order = [slot.track for slot in slots]
    assert tracks_in_order == ["Frontend", "Frontend", "Lifestyle"]
    # Relevance is a valid 0..1 score.
    assert all(0.0 <= slot.relevance <= 1.0 for slot in slots)
    assert isinstance(slots[0], AgendaSlot)


async def test_draft_agenda_empty_event(seeded):
    """An event with no sessions yields an empty draft (no crash)."""
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    event_id = await make_event(maker, t1, name="EmptyConf")
    async with maker() as s:
        svc = DiscoveryService(s)
        slots = await svc.draft_agenda(event_id, "anything", t1)
    assert slots == []


async def test_draft_agenda_unknown_event_raises(seeded):
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    async with maker() as s:
        svc = DiscoveryService(s)
        with pytest.raises(NotFoundError):
            await svc.draft_agenda("missing", "theme", t1)
