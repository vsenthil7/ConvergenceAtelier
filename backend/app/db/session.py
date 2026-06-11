"""Async engine + session factory.

Demo mode uses SQLite (aiosqlite); production can point DATABASE_URL at Postgres
(asyncpg) with no code change. Tables are created on startup for the demo so no
migration step is needed to run; Alembic migrations live alongside for production.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.db.base import Base

engine = create_async_engine(settings.database_url, future=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_models() -> None:
    """Create all tables. Safe to call repeatedly (checkfirst)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields a scoped async session."""
    async with SessionLocal() as session:
        yield session
