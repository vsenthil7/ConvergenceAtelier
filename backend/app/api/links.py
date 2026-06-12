"""Event-link REST endpoints (S7.5), nested under an event.

RBAC:
- list links / catalog : any authenticated user in scope.
- link / unlink        : admins only (Role.USER rejected).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_session
from app.models.identity import Role, User
from app.schemas.link import CatalogSessionRead, LinkedEventRead, LinkRequest
from app.services.errors import ForbiddenError
from app.services.link_service import LinkService

router = APIRouter(prefix="/api/events/{event_id}", tags=["links"])


def _service(session: AsyncSession = Depends(get_session)) -> LinkService:
    return LinkService(session)


def _scope(user: User) -> str | None:
    return None if user.role is Role.SUPER_ADMIN else user.tenant_id


def _require_admin(user: User) -> None:
    if user.role is Role.USER:
        raise ForbiddenError("Only admins can manage event links")


@router.get("/links", response_model=list[LinkedEventRead])
async def list_links(
    event_id: str,
    user: User = Depends(get_current_user),
    svc: LinkService = Depends(_service),
) -> list[LinkedEventRead]:
    events = await svc.linked_events(event_id, _scope(user))
    return [LinkedEventRead.model_validate(e, from_attributes=True) for e in events]


@router.post("/links", response_model=list[LinkedEventRead], status_code=status.HTTP_201_CREATED)
async def create_link(
    event_id: str,
    payload: LinkRequest,
    user: User = Depends(get_current_user),
    svc: LinkService = Depends(_service),
) -> list[LinkedEventRead]:
    _require_admin(user)
    await svc.link(event_id, payload.other_event_id, _scope(user))
    events = await svc.linked_events(event_id, _scope(user))
    return [LinkedEventRead.model_validate(e, from_attributes=True) for e in events]


@router.delete("/links/{other_event_id}", response_model=list[LinkedEventRead])
async def remove_link(
    event_id: str,
    other_event_id: str,
    user: User = Depends(get_current_user),
    svc: LinkService = Depends(_service),
) -> list[LinkedEventRead]:
    _require_admin(user)
    await svc.unlink(event_id, other_event_id, _scope(user))
    events = await svc.linked_events(event_id, _scope(user))
    return [LinkedEventRead.model_validate(e, from_attributes=True) for e in events]


@router.get("/catalog", response_model=list[CatalogSessionRead])
async def combined_catalog(
    event_id: str,
    user: User = Depends(get_current_user),
    svc: LinkService = Depends(_service),
) -> list[CatalogSessionRead]:
    rows = await svc.catalog(event_id, _scope(user))
    return [
        CatalogSessionRead(
            session_id=r.session_id,
            event_id=r.event_id,
            event_name=r.event_name,
            title=r.title,
            track=r.track,
            speaker=r.speaker,
            mode=r.mode,
            stream_url=r.stream_url,
            recording_url=r.recording_url,
            starts_at=r.starts_at,
        )
        for r in rows
    ]
