"""Registration service tests: register/cancel/status/roster + tenant scoping."""
from __future__ import annotations

import pytest

from app.models.identity import Role, User
from app.models.registration import RegistrationStatus
from app.services.errors import NotFoundError
from app.services.registration_service import RegistrationService
from tests.conftest import make_event


async def _user(maker, tenant_id, email="att@x.com"):
    async with maker() as s:
        u = User(email=email, role=Role.USER, tenant_id=tenant_id)
        s.add(u)
        await s.commit()
        await s.refresh(u)
        return u


async def test_register_then_status(seeded):
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    event_id = await make_event(maker, t1, name="Conf")
    user = await _user(maker, t1)
    async with maker() as s:
        svc = RegistrationService(s)
        reg = await svc.register(event_id, user, t1)
        assert reg.status is RegistrationStatus.REGISTERED
        status = await svc.my_status(event_id, user, t1)
        assert status is RegistrationStatus.REGISTERED


async def test_status_none_when_never_registered(seeded):
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    event_id = await make_event(maker, t1, name="Conf")
    user = await _user(maker, t1)
    async with maker() as s:
        svc = RegistrationService(s)
        assert await svc.my_status(event_id, user, t1) is None


async def test_register_is_idempotent_reactivates(seeded):
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    event_id = await make_event(maker, t1, name="Conf")
    user = await _user(maker, t1)
    async with maker() as s:
        svc = RegistrationService(s)
        await svc.register(event_id, user, t1)
        await svc.cancel(event_id, user, t1)
        assert await svc.my_status(event_id, user, t1) is RegistrationStatus.CANCELLED
        # Re-registering flips the same row back, not a duplicate.
        await svc.register(event_id, user, t1)
        assert await svc.my_status(event_id, user, t1) is RegistrationStatus.REGISTERED
    async with maker() as s:
        from sqlalchemy import func, select
        from app.models.registration import EventRegistration

        count = await s.scalar(select(func.count()).select_from(EventRegistration))
    assert count == 1


async def test_cancel_without_registration_raises(seeded):
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    event_id = await make_event(maker, t1, name="Conf")
    user = await _user(maker, t1)
    async with maker() as s:
        svc = RegistrationService(s)
        with pytest.raises(NotFoundError):
            await svc.cancel(event_id, user, t1)


async def test_register_out_of_tenant_scope_raises(seeded):
    """A user scoped to t1 cannot register for a t2 event (event not in scope)."""
    maker = seeded["maker"]
    t1, t2 = seeded["ids"]["t1"], seeded["ids"]["t2"]
    other_event = await make_event(maker, t2, name="OtherConf")
    user = await _user(maker, t1)
    async with maker() as s:
        svc = RegistrationService(s)
        with pytest.raises(NotFoundError):
            await svc.register(other_event, user, t1)


async def test_participants_roster_excludes_cancelled(seeded):
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    event_id = await make_event(maker, t1, name="Conf")
    u1 = await _user(maker, t1, "a@x.com")
    u2 = await _user(maker, t1, "b@x.com")
    async with maker() as s:
        svc = RegistrationService(s)
        await svc.register(event_id, u1, t1)
        await svc.register(event_id, u2, t1)
        await svc.cancel(event_id, u2, t1)
        roster = await svc.participants(event_id, t1)
    emails = [p.email for p in roster]
    assert emails == ["a@x.com"]  # b cancelled, excluded; sorted by email


async def test_super_admin_can_register_across_tenants(seeded):
    maker = seeded["maker"]
    t2 = seeded["ids"]["t2"]
    event_id = await make_event(maker, t2, name="Conf")
    # super-admin user (tenant_id None) registering with scope None
    async with maker() as s:
        su = User(email="su2@x.com", role=Role.SUPER_ADMIN, tenant_id=None)
        s.add(su)
        await s.commit()
        await s.refresh(su)
    async with maker() as s:
        svc = RegistrationService(s)
        reg = await svc.register(event_id, su, None)
        assert reg.status is RegistrationStatus.REGISTERED
