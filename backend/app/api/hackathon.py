"""Hackathon REST endpoints (S7.3), nested under an event.

RBAC:
- list teams / submissions / leaderboard : any authenticated user in scope.
- create team / join team / create+update submission : any authenticated user
  (attendees self-organise); tenant scope still enforced via the event.
- record score : admins/judges only (Role.USER is rejected).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_session
from app.models.identity import Role, User
from app.schemas.hackathon import (
    LeaderboardRow,
    ScoreCreate,
    ScoreRead,
    SubmissionCreate,
    SubmissionRead,
    SubmissionUpdate,
    TeamCreate,
    TeamMemberRead,
    TeamRead,
)
from app.services.errors import ForbiddenError
from app.services.hackathon_service import HackathonService

router = APIRouter(prefix="/api/events/{event_id}/hackathon", tags=["hackathon"])


def _service(session: AsyncSession = Depends(get_session)) -> HackathonService:
    return HackathonService(session)


def _scope(user: User) -> str | None:
    return None if user.role is Role.SUPER_ADMIN else user.tenant_id


def _team_read(team) -> TeamRead:
    return TeamRead(
        id=team.id,
        event_id=team.event_id,
        name=team.name,
        members=[
            TeamMemberRead(
                user_id=m.user.id, email=m.user.email, full_name=m.user.full_name
            )
            for m in team.members
        ],
    )


# ---------- teams ----------

@router.get("/teams", response_model=list[TeamRead])
async def list_teams(
    event_id: str,
    user: User = Depends(get_current_user),
    svc: HackathonService = Depends(_service),
) -> list[TeamRead]:
    teams = await svc.list_teams(event_id, _scope(user))
    return [_team_read(t) for t in teams]


@router.post("/teams", response_model=TeamRead, status_code=status.HTTP_201_CREATED)
async def create_team(
    event_id: str,
    payload: TeamCreate,
    user: User = Depends(get_current_user),
    svc: HackathonService = Depends(_service),
) -> TeamRead:
    team = await svc.create_team(event_id, _scope(user), payload)
    return _team_read(team)


@router.post("/teams/{team_id}/join", response_model=TeamRead)
async def join_team(
    event_id: str,
    team_id: str,
    user: User = Depends(get_current_user),
    svc: HackathonService = Depends(_service),
) -> TeamRead:
    team = await svc.join_team(event_id, team_id, user, _scope(user))
    return _team_read(team)


# ---------- submissions ----------

@router.get("/submissions", response_model=list[SubmissionRead])
async def list_submissions(
    event_id: str,
    user: User = Depends(get_current_user),
    svc: HackathonService = Depends(_service),
) -> list[SubmissionRead]:
    subs = await svc.list_submissions(event_id, _scope(user))
    return [SubmissionRead.model_validate(s) for s in subs]


@router.post(
    "/teams/{team_id}/submission",
    response_model=SubmissionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_submission(
    event_id: str,
    team_id: str,
    payload: SubmissionCreate,
    user: User = Depends(get_current_user),
    svc: HackathonService = Depends(_service),
) -> SubmissionRead:
    sub = await svc.create_submission(event_id, team_id, _scope(user), payload)
    return SubmissionRead.model_validate(sub)


@router.patch("/submissions/{submission_id}", response_model=SubmissionRead)
async def update_submission(
    event_id: str,
    submission_id: str,
    payload: SubmissionUpdate,
    user: User = Depends(get_current_user),
    svc: HackathonService = Depends(_service),
) -> SubmissionRead:
    sub = await svc.update_submission(event_id, submission_id, _scope(user), payload)
    return SubmissionRead.model_validate(sub)


# ---------- scoring ----------

@router.post(
    "/submissions/{submission_id}/scores",
    response_model=ScoreRead,
    status_code=status.HTTP_201_CREATED,
)
async def record_score(
    event_id: str,
    submission_id: str,
    payload: ScoreCreate,
    user: User = Depends(get_current_user),
    svc: HackathonService = Depends(_service),
) -> ScoreRead:
    if user.role is Role.USER:
        raise ForbiddenError("Only judges can score submissions")
    score = await svc.record_score(
        event_id, submission_id, user, _scope(user), payload.criterion, payload.value
    )
    return ScoreRead.model_validate(score)


# ---------- leaderboard ----------

@router.get("/leaderboard", response_model=list[LeaderboardRow])
async def leaderboard(
    event_id: str,
    user: User = Depends(get_current_user),
    svc: HackathonService = Depends(_service),
) -> list[LeaderboardRow]:
    rows = await svc.leaderboard(event_id, _scope(user))
    return [
        LeaderboardRow(
            team_id=r.team_id,
            team_name=r.team_name,
            submission_id=r.submission_id,
            submission_title=r.submission_title,
            status=r.status,
            total_score=r.total_score,
            average_score=r.average_score,
            score_count=r.score_count,
            rank=r.rank,
        )
        for r in rows
    ]
