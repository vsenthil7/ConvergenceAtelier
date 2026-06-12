"""Health + readiness endpoints (DB-aware)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.config import settings
from app.db.base import utcnow
from app.db.session import get_session
from app.models.identity import Tenant, User

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health() -> dict[str, object]:
    """Liveness: process is up. Cheap, no dependencies."""
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": __version__,
        "mode": "mock" if settings.use_mocks else "live",
        "time": utcnow().isoformat(),
    }


@router.get("/api/ready")
async def ready(session: AsyncSession = Depends(get_session)) -> dict[str, object]:
    """Readiness: verifies DB connectivity and reports tenant/user counts."""
    tenants = await session.scalar(select(func.count()).select_from(Tenant))
    users = await session.scalar(select(func.count()).select_from(User))
    return {
        "status": "ready",
        "database": "ok",
        "tenants": int(tenants or 0),
        "users": int(users or 0),
        "google_oauth": settings.google_oauth_enabled,
        "time": utcnow().isoformat(),
    }
