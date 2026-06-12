"""Hackathon module models (S7.3): teams, submissions, judging scores.

These hang off an event whose ``event_type`` is HACKATHON, but they reference the
shared Event/User core rather than forking it (composition over duplication).

- Team           : an event-scoped squad with a name.
- TeamMember     : membership join (team x user), unique per pair.
- Submission     : a team's project (title/summary/repo/demo) with a status.
- Score          : a judge's score for a submission on a named criterion.

Everything is timezone-aware via TimestampMixin.
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.event import Event
from app.models.identity import User


def _uuid() -> str:
    return uuid.uuid4().hex


class SubmissionStatus(str, enum.Enum):
    """Lifecycle of a hackathon project submission."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    DISQUALIFIED = "disqualified"


class Team(TimestampMixin, Base):
    """A hackathon team within an event."""

    __tablename__ = "teams"
    __table_args__ = (
        UniqueConstraint("event_id", "name", name="uq_team_event_name"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    event_id: Mapped[str] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    event: Mapped[Event] = relationship()
    members: Mapped[list["TeamMember"]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )
    submission: Mapped["Submission | None"] = relationship(
        back_populates="team", cascade="all, delete-orphan", uselist=False
    )


class TeamMember(TimestampMixin, Base):
    """Membership of a user in a team (unique per team+user)."""

    __tablename__ = "team_members"
    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_team_member"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    team: Mapped[Team] = relationship(back_populates="members")
    user: Mapped[User] = relationship()


class Submission(TimestampMixin, Base):
    """A team's project submission (one per team)."""

    __tablename__ = "submissions"
    __table_args__ = (
        UniqueConstraint("team_id", name="uq_submission_team"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    repo_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    demo_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus),
        default=SubmissionStatus.DRAFT,
        nullable=False,
    )

    team: Mapped[Team] = relationship(back_populates="submission")
    scores: Mapped[list["Score"]] = relationship(
        back_populates="submission", cascade="all, delete-orphan"
    )


class Score(TimestampMixin, Base):
    """A judge's score for a submission on a single rubric criterion.

    Unique per (submission, judge, criterion) so re-scoring updates in place.
    """

    __tablename__ = "scores"
    __table_args__ = (
        UniqueConstraint(
            "submission_id", "judge_id", "criterion", name="uq_score_judge_criterion"
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    submission_id: Mapped[str] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    judge_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    criterion: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)

    submission: Mapped[Submission] = relationship(back_populates="scores")
    judge: Mapped[User] = relationship()
