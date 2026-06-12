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
from app.schemas.registration import (
    MyRegistrationStatus,
    ParticipantRead,
    RegistrationRead,
)
from app.services.errors import ForbiddenError
from app.services.event_service import EventService
from app.services.registration_service import RegistrationService

router = APIRouter(prefix="/api/events", tags=["events"])


def _service(session: AsyncSession = Depends(get_session)) -> EventService:
    return EventService(session)


def _reg_service(session: AsyncSession = Depends(get_session)) -> RegistrationService:
    return RegistrationService(session)


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


@router.get("/{event_id}/recordings", response_model=list[SessionRead])
async def event_recordings(
    event_id: str,
    user: User = Depends(get_current_user),
    svc: EventService = Depends(_service),
) -> list[SessionRead]:
    """On-demand catalog: every session in the event that has a recording (S7.2).

    Readable by any authenticated user in scope (attendee-facing).
    """
    rows = await svc.list_recordings(event_id, _read_scope(user))
    return [SessionRead.model_validate(s) for s in rows]


# ---------- registration / participation (S3b) ----------


@router.post(
    "/{event_id}/register",
    response_model=RegistrationRead,
    status_code=status.HTTP_201_CREATED,
)
async def register_for_event(
    event_id: str,
    user: User = Depends(get_current_user),
    svc: RegistrationService = Depends(_reg_service),
) -> RegistrationRead:
    """Any authenticated user registers themselves for an in-scope event."""
    reg = await svc.register(event_id, user, _read_scope(user))
    return RegistrationRead.model_validate(reg)


@router.delete("/{event_id}/register", response_model=RegistrationRead)
async def cancel_registration(
    event_id: str,
    user: User = Depends(get_current_user),
    svc: RegistrationService = Depends(_reg_service),
) -> RegistrationRead:
    reg = await svc.cancel(event_id, user, _read_scope(user))
    return RegistrationRead.model_validate(reg)


@router.get("/{event_id}/registration", response_model=MyRegistrationStatus)
async def my_registration(
    event_id: str,
    user: User = Depends(get_current_user),
    svc: RegistrationService = Depends(_reg_service),
) -> MyRegistrationStatus:
    """The caller's own registration status for an event."""
    status_value = await svc.my_status(event_id, user, _read_scope(user))
    return MyRegistrationStatus(event_id=event_id, status=status_value)


@router.get("/{event_id}/participants", response_model=list[ParticipantRead])
async def event_participants(
    event_id: str,
    user: User = Depends(get_current_user),
    svc: RegistrationService = Depends(_reg_service),
) -> list[ParticipantRead]:
    """Roster of registered attendees (admins only)."""
    if user.role is Role.USER:
        raise ForbiddenError("Only admins can view the participant roster")
    rows = await svc.participants(event_id, _read_scope(user))
    return [
        ParticipantRead(
            user_id=p.user_id,
            email=p.email,
            full_name=p.full_name,
            status=p.status,
        )
        for p in rows
    ]
