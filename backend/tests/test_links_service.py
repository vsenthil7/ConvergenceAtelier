"""Direct LinkService + linked-discovery tests (deterministic, no ASGI)."""
from __future__ import annotations

import pytest

from app.models.identity import Role, User
from app.services.discovery_service import DiscoveryService
from app.services.errors import ConflictError, NotFoundError
from app.services.link_service import LinkService, _canonical
from tests.conftest import make_event, make_session


def test_canonical_orders_pair():
    assert _canonical("b", "a") == ("a", "b")
    assert _canonical("a", "b") == ("a", "b")


async def test_link_is_symmetric_regardless_of_direction(seeded):
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    e1 = await make_event(maker, t1, "A")
    e2 = await make_event(maker, t1, "B")
    async with maker() as s:
        svc = LinkService(s)
        # link in the "larger first" direction; canonical order still applies
        await svc.link(e2, e1, t1)
        from_e1 = await svc.linked_events(e1, t1)
        from_e2 = await svc.linked_events(e2, t1)
    assert [e.id for e in from_e1] == [e2]
    assert [e.id for e in from_e2] == [e1]


async def test_self_link_raises(seeded):
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    e1 = await make_event(maker, t1, "A")
    async with maker() as s:
        svc = LinkService(s)
        with pytest.raises(ConflictError):
            await svc.link(e1, e1, t1)


async def test_duplicate_link_raises(seeded):
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    e1 = await make_event(maker, t1, "A")
    e2 = await make_event(maker, t1, "B")
    async with maker() as s:
        svc = LinkService(s)
        await svc.link(e1, e2, t1)
        with pytest.raises(ConflictError):
            await svc.link(e1, e2, t1)


async def test_unlink_missing_raises(seeded):
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    e1 = await make_event(maker, t1, "A")
    e2 = await make_event(maker, t1, "B")
    async with maker() as s:
        svc = LinkService(s)
        with pytest.raises(NotFoundError):
            await svc.unlink(e1, e2, t1)


async def test_no_links_returns_empty(seeded):
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    e1 = await make_event(maker, t1, "Solo")
    async with maker() as s:
        svc = LinkService(s)
        assert await svc.linked_events(e1, t1) == []


async def test_catalog_combines_and_tags(seeded):
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    e1 = await make_event(maker, t1, "Flagship")
    e2 = await make_event(maker, t1, "Online")
    await make_session(maker, e1, title="Talk One")
    await make_session(maker, e2, title="Talk Two")
    async with maker() as s:
        svc = LinkService(s)
        await svc.link(e1, e2, t1)
        catalog = await svc.catalog(e1, t1)
    assert {c.title for c in catalog} == {"Talk One", "Talk Two"}
    assert {c.event_name for c in catalog} == {"Flagship", "Online"}


async def test_discovery_recommend_across_links(seeded):
    """recommend_across_links pulls candidates from the event AND its linked set."""
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    e1 = await make_event(maker, t1, "Flagship")
    e2 = await make_event(maker, t1, "Online")
    await make_session(maker, e1, title="React performance tuning", track="FE", speaker="Ada")
    await make_session(maker, e2, title="React server components deep dive", track="FE", speaker="Lee")
    async with maker() as s:
        link = LinkService(s)
        await link.link(e1, e2, t1)
    async with maker() as s:
        disc = DiscoveryService(s)
        recs = await disc.recommend_across_links(e1, "react performance", t1, limit=5)
    titles = {r.session.title for r in recs}
    # candidates include the linked event's session
    assert "React server components deep dive" in titles
    assert "React performance tuning" in titles
    # top hit is the most on-topic
    assert recs[0].session.title == "React performance tuning"
