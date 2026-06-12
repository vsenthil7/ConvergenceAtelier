"""Convergence Atelier API entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.auth import router as auth_router
from app.api.errors import (
    conflict_handler,
    forbidden_handler,
    not_found_handler,
    unauthorized_handler,
)
from app.api.events import router as events_router
from app.api.health import router as health_router
from app.config import settings
from app.db.session import SessionLocal, init_models
from app.services.errors import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
)
from app.services.seed import seed_demo


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_models()
    if settings.seed_demo_data:
        async with SessionLocal() as session:
            await seed_demo(session)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(NotFoundError, not_found_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ConflictError, conflict_handler)  # type: ignore[arg-type]
    app.add_exception_handler(UnauthorizedError, unauthorized_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ForbiddenError, forbidden_handler)  # type: ignore[arg-type]

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(events_router)
    return app


app = create_app()
