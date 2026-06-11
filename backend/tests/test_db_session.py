"""Cover the runtime DB bootstrap (init_models + get_session)."""
from __future__ import annotations

import app.db.session as db_session


async def test_init_models_and_get_session(monkeypatch, tmp_path):
    # Point the module engine at a temp sqlite file so we don't touch the real db.
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    test_engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'cover.db'}", future=True
    )
    monkeypatch.setattr(db_session, "engine", test_engine)
    monkeypatch.setattr(
        db_session,
        "SessionLocal",
        async_sessionmaker(test_engine, expire_on_commit=False),
    )

    await db_session.init_models()

    gen = db_session.get_session()
    session = await gen.__anext__()
    assert session is not None
    await gen.aclose()
    await test_engine.dispose()
