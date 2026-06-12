"""Event + agenda REST endpoints (authenticated + tenant-scoped).

Scope rule: super-admins span all tenants (tenant_id=None); everyone else is
confined to their own tenant. Writes require a tenant context.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_session
from app.models.identity import Role, User
from app.schemas.event import (
    EventCreate,
    EventRead,
    EventUpdate,
    SessionCreate,
    SessionRead,
)
from app.services.errors import ForbiddenError
from app.services.event_service import EventService

router = APIRouter(prefix="/api/events", tags=["events"])


def _service(session: AsyncSession = Depends(get_session)) -> EventService:
    return EventService(session)


def _read_scope(user: User) -> str | None:
    """Tenant filter for reads: None for super-admin (all), else own tenant."""
    return None if user.role is Role.SUPER_ADMIN else user.tenant_id


def _write_tenant(user: User) -> str:
    """Tenant a write lands in. Super-admins must belong to a tenant to create."""
    if user.tenant_id is None:
        raise ForbiddenError("No tenant context for this operation")
    return user.tenant_id


@router.get("", response_model=list[EventRead])
async def list_events(
    user: User = Depends(get_current_user), svc: EventService = Depends(_service)
) -> list[EventRead]:
    events = await svc.list_events(_read_scope(user))
    return [EventRead.model_validate(e) for e in events]


@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: EventCreate,
    user: User = Depends(get_current_user),
    svc: EventService = Depends(_service),
) -> EventRead:
    if user.role is Role.USER:
        raise ForbiddenError("Users cannot create events")
    return EventRead.model_validate(await svc.create_event(_write_tenant(user), payload))


@router.get("/{event_id}", response_model=EventRead)
async def get_event(
    event_id: str,
    user: User = Depends(get_current_user),
    svc: EventService = Depends(_service),
) -> EventRead:
    return EventRead.model_validate(await svc.get_event(event_id, _read_scope(user)))


@router.patch("/{event_id}", response_model=EventRead)
async def update_event(
    event_id: str,
    payload: EventUpdate,
    user: User = Depends(get_current_user),
    svc: EventService = Depends(_service),
) -> EventRead:
    if user.role is Role.USER:
        raise ForbiddenError("Users cannot edit events")
    return EventRead.model_validate(
        await svc.update_event(event_id, _read_scope(user), payload)
    )


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: str,
    user: User = Depends(get_current_user),
    svc: EventService = Depends(_service),
) -> None:
    if user.role is Role.USER:
        raise ForbiddenError("Users cannot delete events")
    await svc.delete_event(event_id, _read_scope(user))


@router.post(
    "/{event_id}/sessions",
    response_model=SessionRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_session(
    event_id: str,
    payload: SessionCreate,
    user: User = Depends(get_current_user),
    svc: EventService = Depends(_service),
) -> SessionRead:
    if user.role is Role.USER:
        raise ForbiddenError("Users cannot add sessions")
    return SessionRead.model_validate(
        await svc.add_session(event_id, _read_scope(user), payload)
    )
