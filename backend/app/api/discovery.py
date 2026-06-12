"""AI discovery endpoints: recommendations + matchmaking (authenticated).

All endpoints are tenant-scoped (super-admins span all tenants) and available to
every authenticated role — discovery is primarily an attendee-facing feature.
Runs keyless in demo mode via the local embedder.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_session
from app.models.identity import Role, User
from app.schemas.discovery import (
    AttendeeMatchRead,
    AttendeeRef,
    InterestQuery,
    MatchRequest,
    ScoredSessionRead,
)
from app.schemas.event import SessionRead
from app.services.discovery_service import AttendeeProfile, DiscoveryService

router = APIRouter(prefix="/api/discovery", tags=["discovery"])


def _service(session: AsyncSession = Depends(get_session)) -> DiscoveryService:
    return DiscoveryService(session)


def _read_scope(user: User) -> str | None:
    return None if user.role is Role.SUPER_ADMIN else user.tenant_id


def _to_scored(items) -> list[ScoredSessionRead]:
    return [
        ScoredSessionRead(score=round(i.score, 4), session=SessionRead.model_validate(i.session))
        for i in items
    ]


@router.get("/sessions/{session_id}/similar", response_model=list[ScoredSessionRead])
async def similar_sessions(
    session_id: str,
    limit: int = 5,
    user: User = Depends(get_current_user),
    svc: DiscoveryService = Depends(_service),
) -> list[ScoredSessionRead]:
    items = await svc.recommend_for_session(session_id, _read_scope(user), limit)
    return _to_scored(items)


@router.post("/recommend", response_model=list[ScoredSessionRead])
async def recommend_for_interests(
    payload: InterestQuery,
    user: User = Depends(get_current_user),
    svc: DiscoveryService = Depends(_service),
) -> list[ScoredSessionRead]:
    items = await svc.recommend_for_interests(
        payload.interests, _read_scope(user), payload.limit
    )
    return _to_scored(items)


@router.post("/match", response_model=list[AttendeeMatchRead])
async def match_attendees(
    payload: MatchRequest,
    user: User = Depends(get_current_user),
    svc: DiscoveryService = Depends(_service),
) -> list[AttendeeMatchRead]:
    profiles = [
        AttendeeProfile(id=a.id, name=a.name, interests=a.interests)
        for a in payload.attendees
    ]
    matches = svc.match_attendees(profiles, payload.limit)
    return [
        AttendeeMatchRead(
            score=round(m.score, 4),
            a=AttendeeRef(id=m.a.id, name=m.a.name),
            b=AttendeeRef(id=m.b.id, name=m.b.name),
        )
        for m in matches
    ]
