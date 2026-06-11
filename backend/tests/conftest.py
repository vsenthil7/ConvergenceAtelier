"""Shared test fixtures: isolated in-memory DB + client per test."""
from __future__ import annotations

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_session
from app.main import create_app


@pytest.fixture
async def client():
    # Fresh in-memory SQLite per test for full isolation.
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    testing_session = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_session():
        async with testing_session() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = override_get_session
    # Skip the lifespan's init_models (we built the schema above).
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await engine.dispose()


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
