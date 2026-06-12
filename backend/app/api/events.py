"""Event + agenda REST endpoints.

404s are handled centrally by the NotFoundError exception handler registered in
app.main, so each route stays a single clean expression.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.event import (
    EventCreate,
    EventRead,
    EventUpdate,
    SessionCreate,
    SessionRead,
)
from app.services.event_service import EventService

router = APIRouter(prefix="/api/events", tags=["events"])


def _service(session: AsyncSession = Depends(get_session)) -> EventService:
    return EventService(session)


@router.get("", response_model=list[EventRead])
async def list_events(svc: EventService = Depends(_service)) -> list[EventRead]:
    return [EventRead.model_validate(e) for e in await svc.list_events()]


@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: EventCreate, svc: EventService = Depends(_service)
) -> EventRead:
    return EventRead.model_validate(await svc.create_event(payload))


@router.get("/{event_id}", response_model=EventRead)
async def get_event(event_id: str, svc: EventService = Depends(_service)) -> EventRead:
    return EventRead.model_validate(await svc.get_event(event_id))


@router.patch("/{event_id}", response_model=EventRead)
async def update_event(
    event_id: str, payload: EventUpdate, svc: EventService = Depends(_service)
) -> EventRead:
    return EventRead.model_validate(await svc.update_event(event_id, payload))


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(event_id: str, svc: EventService = Depends(_service)) -> None:
    await svc.delete_event(event_id)


@router.post(
    "/{event_id}/sessions",
    response_model=SessionRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_session(
    event_id: str, payload: SessionCreate, svc: EventService = Depends(_service)
) -> SessionRead:
    return SessionRead.model_validate(await svc.add_session(event_id, payload))
