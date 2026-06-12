"""Shared test fixtures: isolated in-memory DB + per-role authenticated clients."""
from __future__ import annotations

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_session
from app.main import create_app
from app.models.event import Event, Session
from app.models.identity import Role, Tenant, User


@pytest.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    yield maker
    await engine.dispose()


@pytest.fixture
async def seeded(db):
    """Two tenants, a super-admin, and per-tenant admin/user. Returns ids + maker."""
    maker = db
    async with maker() as s:
        t1 = Tenant(name="React Org", slug="react-org")
        t2 = Tenant(name="Vue Org", slug="vue-org")
        s.add_all([t1, t2])
        await s.flush()
        pw = hash_password("Secret123!")
        sa = User(email="super@x.com", password_hash=pw, role=Role.SUPER_ADMIN, tenant_id=None)
        a1 = User(email="a1@x.com", password_hash=pw, role=Role.TENANT_ADMIN, tenant_id=t1.id)
        a2 = User(email="a2@x.com", password_hash=pw, role=Role.TENANT_ADMIN, tenant_id=t2.id)
        u1 = User(email="u1@x.com", password_hash=pw, role=Role.USER, tenant_id=t1.id)
        s.add_all([sa, a1, a2, u1])
        await s.flush()
        ids = {
            "t1": t1.id, "t2": t2.id,
            "sa": sa.id, "a1": a1.id, "a2": a2.id, "u1": u1.id,
        }
        await s.commit()
    return {"maker": maker, "ids": ids}


def _token(user_id: str, role: Role, tenant_id: str | None) -> str:
    return create_access_token(user_id, {"role": role.value, "tenant_id": tenant_id})


@pytest.fixture
def make_client():
    """Factory: build an httpx client bound to a maker, optionally authed as a user."""

    def _factory(maker, auth_header: str | None = None):
        app = create_app()

        async def override_get_session():
            async with maker() as session:
                yield session

        app.dependency_overrides[get_session] = override_get_session
        headers = {"Authorization": auth_header} if auth_header else {}
        transport = httpx.ASGITransport(app=app)
        return httpx.AsyncClient(transport=transport, base_url="http://test", headers=headers)

    return _factory


def bearer(user_id: str, role: Role, tenant_id: str | None) -> str:
    return f"Bearer {_token(user_id, role, tenant_id)}"


async def make_event(maker, tenant_id: str, name: str = "Conf") -> str:
    from datetime import datetime, timezone

    async with maker() as s:
        e = Event(
            tenant_id=tenant_id,
            name=name,
            starts_at=datetime(2026, 6, 11, 9, tzinfo=timezone.utc),
            ends_at=datetime(2026, 6, 12, 17, tzinfo=timezone.utc),
        )
        s.add(e)
        await s.commit()
        await s.refresh(e)
        return e.id


def event_payload(**overrides):
    base = {
        "name": "React Summit",
        "location": "Amsterdam",
        "description": "JS conference",
        "starts_at": "2026-06-11T09:00:00+00:00",
        "ends_at": "2026-06-12T17:00:00+00:00",
    }
    base.update(overrides)
    return base


def session_payload(**overrides):
    base = {
        "title": "Keynote",
        "track": "Main",
        "speaker": "Jane Dev",
        "starts_at": "2026-06-11T10:00:00+00:00",
        "ends_at": "2026-06-11T11:00:00+00:00",
    }
    base.update(overrides)
    return base


# Re-export Session for tests that build agenda items directly.
__all__ = ["Session"]
