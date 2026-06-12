"""Webinar REST endpoints (S7.4), nested under an event.

RBAC:
- status / reminders / register / cancel : any authenticated user in scope.
- waitlist roster : admins only (Role.USER rejected).

Register/cancel here are capacity-aware (overflow waitlists; cancel auto-promotes),
distinct from the plain S3b register endpoints.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_session
from app.models.identity import Role, User
from app.schemas.webinar import (
    ReminderRead,
    WaitlistEntryRead,
    WebinarRegistrationRead,
    WebinarStatusRead,
)
from app.services.errors import ForbiddenError
from app.services.webinar_service import WebinarService

router = APIRouter(prefix="/api/events/{event_id}/webinar", tags=["webinar"])


def _service(session: AsyncSession = Depends(get_session)) -> WebinarService:
    return WebinarService(session)


def _scope(user: User) -> str | None:
    return None if user.role is Role.SUPER_ADMIN else user.tenant_id


@router.get("/status", response_model=WebinarStatusRead)
async def webinar_status(
    event_id: str,
    user: User = Depends(get_current_user),
    svc: WebinarService = Depends(_service),
) -> WebinarStatusRead:
    s = await svc.status(event_id, user, _scope(user))
    return WebinarStatusRead(
        event_id=event_id,
        capacity=s.capacity,
        registered_count=s.registered_count,
        waitlisted_count=s.waitlisted_count,
        seats_left=s.seats_left,
        my_state=s.my_state,
        stream_url=s.stream_url,
    )


@router.post(
    "/register",
    response_model=WebinarRegistrationRead,
    status_code=status.HTTP_201_CREATED,
)
async def webinar_register(
    event_id: str,
    user: User = Depends(get_current_user),
    svc: WebinarService = Depends(_service),
) -> WebinarRegistrationRead:
    reg = await svc.register(event_id, user, _scope(user))
    return WebinarRegistrationRead(event_id=event_id, status=reg.status)


@router.delete("/register", response_model=WebinarRegistrationRead)
async def webinar_cancel(
    event_id: str,
    user: User = Depends(get_current_user),
    svc: WebinarService = Depends(_service),
) -> WebinarRegistrationRead:
    reg = await svc.cancel(event_id, user, _scope(user))
    return WebinarRegistrationRead(event_id=event_id, status=reg.status)


@router.get("/waitlist", response_model=list[WaitlistEntryRead])
async def webinar_waitlist(
    event_id: str,
    user: User = Depends(get_current_user),
    svc: WebinarService = Depends(_service),
) -> list[WaitlistEntryRead]:
    if user.role is Role.USER:
        raise ForbiddenError("Only admins can view the waitlist")
    rows = await svc.waitlist(event_id, _scope(user))
    return [
        WaitlistEntryRead(
            user_id=r.user_id, email=r.email, full_name=r.full_name, position=r.position
        )
        for r in rows
    ]


@router.get("/reminders", response_model=list[ReminderRead])
async def webinar_reminders(
    event_id: str,
    user: User = Depends(get_current_user),
    svc: WebinarService = Depends(_service),
) -> list[ReminderRead]:
    rows = await svc.reminders(event_id, _scope(user))
    return [ReminderRead(offset=r.offset, send_at=r.send_at) for r in rows]
