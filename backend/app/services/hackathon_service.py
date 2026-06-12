"""Hackathon service (S7.3): teams, submissions, judging, leaderboard.

All operations are tenant-safe: they resolve the event through EventService
(which raises NotFound when the event is outside the caller's tenant), so a team
or submission can never be created against an out-of-scope event.

Leaderboard is computed deterministically from scores: per submission we sum and
average the judges' criterion scores, then rank by total (descending), breaking
ties by average then title for stability.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.hackathon import (
    Score,
    Submission,
    SubmissionStatus,
    Team,
    TeamMember,
)
from app.models.identity import User
from app.schemas.hackathon import SubmissionCreate, SubmissionUpdate, TeamCreate
from app.services.errors import ConflictError, NotFoundError
from app.services.event_service import EventService


@dataclass(frozen=True)
class LeaderboardEntry:
    team_id: str
    team_name: str
    submission_id: str
    submission_title: str
    status: SubmissionStatus
    total_score: float
    average_score: float
    score_count: int
    rank: int


class HackathonService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.events = EventService(session)

    async def _event_scope(self, event_id: str, tenant_id: str | None) -> None:
        await self.events.get_event(event_id, tenant_id)  # raises NotFound if out of scope

    # ---------- teams ----------

    async def create_team(
        self, event_id: str, tenant_id: str | None, data: TeamCreate
    ) -> Team:
        await self._event_scope(event_id, tenant_id)
        existing = await self.session.execute(
            select(Team).where(Team.event_id == event_id, Team.name == data.name)
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictError("Team", data.name)
        team = Team(event_id=event_id, name=data.name)
        self.session.add(team)
        await self.session.commit()
        return await self._get_team(team.id)

    async def _get_team(self, team_id: str) -> Team:
        result = await self.session.execute(
            select(Team)
            .options(selectinload(Team.members).selectinload(TeamMember.user))
            .where(Team.id == team_id)
        )
        team = result.scalar_one_or_none()
        if team is None:
            raise NotFoundError("Team", team_id)
        return team

    async def list_teams(self, event_id: str, tenant_id: str | None) -> list[Team]:
        await self._event_scope(event_id, tenant_id)
        result = await self.session.execute(
            select(Team)
            .options(selectinload(Team.members).selectinload(TeamMember.user))
            .where(Team.event_id == event_id)
            .order_by(Team.name)
        )
        return list(result.scalars().all())

    async def join_team(
        self, event_id: str, team_id: str, user: User, tenant_id: str | None
    ) -> Team:
        await self._event_scope(event_id, tenant_id)
        team = await self._get_team(team_id)
        if team.event_id != event_id:
            raise NotFoundError("Team", team_id)
        already = await self.session.execute(
            select(TeamMember).where(
                TeamMember.team_id == team_id, TeamMember.user_id == user.id
            )
        )
        if already.scalar_one_or_none() is None:
            self.session.add(TeamMember(team_id=team_id, user_id=user.id))
            await self.session.commit()
        # Drop cached instances so the reload reflects the new membership row
        # (an already-loaded members collection would otherwise stay stale).
        self.session.expire_all()
        return await self._get_team(team_id)

    # ---------- submissions ----------

    async def create_submission(
        self, event_id: str, team_id: str, tenant_id: str | None, data: SubmissionCreate
    ) -> Submission:
        await self._event_scope(event_id, tenant_id)
        team = await self._get_team(team_id)
        if team.event_id != event_id:
            raise NotFoundError("Team", team_id)
        existing = await self.session.execute(
            select(Submission).where(Submission.team_id == team_id)
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictError("Submission", team_id)
        submission = Submission(
            team_id=team_id,
            title=data.title,
            summary=data.summary,
            repo_url=data.repo_url,
            demo_url=data.demo_url,
            status=SubmissionStatus.DRAFT,
        )
        self.session.add(submission)
        await self.session.commit()
        await self.session.refresh(submission)
        return submission

    async def _get_submission(self, submission_id: str) -> Submission:
        result = await self.session.execute(
            select(Submission).where(Submission.id == submission_id)
        )
        submission = result.scalar_one_or_none()
        if submission is None:
            raise NotFoundError("Submission", submission_id)
        return submission

    async def update_submission(
        self,
        event_id: str,
        submission_id: str,
        tenant_id: str | None,
        data: SubmissionUpdate,
    ) -> Submission:
        await self._event_scope(event_id, tenant_id)
        submission = await self._get_submission(submission_id)
        # exclude_unset drops fields the caller never set; exclude_none also drops
        # explicit nulls so a partial update can't blank a non-nullable column.
        changes = data.model_dump(exclude_unset=True, exclude_none=True)
        for field, value in changes.items():
            setattr(submission, field, value)
        await self.session.commit()
        await self.session.refresh(submission)
        return submission

    async def list_submissions(
        self, event_id: str, tenant_id: str | None
    ) -> list[Submission]:
        await self._event_scope(event_id, tenant_id)
        result = await self.session.execute(
            select(Submission)
            .join(Team, Team.id == Submission.team_id)
            .where(Team.event_id == event_id)
            .order_by(Submission.title)
        )
        return list(result.scalars().all())

    # ---------- scoring ----------

    async def record_score(
        self,
        event_id: str,
        submission_id: str,
        judge: User,
        tenant_id: str | None,
        criterion: str,
        value: float,
    ) -> Score:
        await self._event_scope(event_id, tenant_id)
        await self._get_submission(submission_id)
        existing = await self.session.execute(
            select(Score).where(
                Score.submission_id == submission_id,
                Score.judge_id == judge.id,
                Score.criterion == criterion,
            )
        )
        score = existing.scalar_one_or_none()
        if score is None:
            score = Score(
                submission_id=submission_id,
                judge_id=judge.id,
                criterion=criterion,
                value=value,
            )
            self.session.add(score)
        else:
            score.value = value  # re-scoring updates in place
        await self.session.commit()
        await self.session.refresh(score)
        return score

    # ---------- leaderboard ----------

    async def leaderboard(
        self, event_id: str, tenant_id: str | None
    ) -> list[LeaderboardEntry]:
        await self._event_scope(event_id, tenant_id)
        result = await self.session.execute(
            select(Submission, Team)
            .join(Team, Team.id == Submission.team_id)
            .options(selectinload(Submission.scores))
            .where(Team.event_id == event_id)
        )
        rows = result.all()
        entries: list[LeaderboardEntry] = []
        for submission, team in rows:
            values = [s.value for s in submission.scores]
            total = float(sum(values))
            count = len(values)
            avg = total / count if count else 0.0
            entries.append(
                LeaderboardEntry(
                    team_id=team.id,
                    team_name=team.name,
                    submission_id=submission.id,
                    submission_title=submission.title,
                    status=submission.status,
                    total_score=total,
                    average_score=avg,
                    score_count=count,
                    rank=0,  # assigned below
                )
            )
        # Rank by total desc, then average desc, then title for stable ordering.
        entries.sort(
            key=lambda e: (-e.total_score, -e.average_score, e.submission_title)
        )
        return [
            LeaderboardEntry(
                team_id=e.team_id,
                team_name=e.team_name,
                submission_id=e.submission_id,
                submission_title=e.submission_title,
                status=e.status,
                total_score=e.total_score,
                average_score=e.average_score,
                score_count=e.score_count,
                rank=i + 1,
            )
            for i, e in enumerate(entries)
        ]
