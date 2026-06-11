"""Convergence Atelier API entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.events import router as events_router
from app.config import settings
from app.db.base import utcnow
from app.db.session import init_models


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_models()
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

    @app.get("/api/health")
    async def health() -> dict[str, object]:
        return {
            "status": "ok",
            "service": settings.app_name,
            "version": __version__,
            "mode": "mock" if settings.use_mocks else "live",
            "time": utcnow().isoformat(),
        }

    app.include_router(events_router)
    return app


app = create_app()
