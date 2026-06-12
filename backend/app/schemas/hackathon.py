"""Request/response schemas for the hackathon module (S7.3)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.models.hackathon import SubmissionStatus


# ---------- teams ----------

class TeamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class TeamMemberRead(BaseModel):
    user_id: str
    email: str
    full_name: str


class TeamRead(BaseModel):
    id: str
    event_id: str
    name: str
    members: list[TeamMemberRead] = []


# ---------- submissions ----------

class SubmissionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(default="", max_length=5000)
    repo_url: str = Field(default="", max_length=500)
    demo_url: str = Field(default="", max_length=500)


class SubmissionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    summary: str | None = Field(default=None, max_length=5000)
    repo_url: str | None = Field(default=None, max_length=500)
    demo_url: str | None = Field(default=None, max_length=500)
    status: SubmissionStatus | None = None


class SubmissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    team_id: str
    title: str
    summary: str
    repo_url: str
    demo_url: str
    status: SubmissionStatus


# ---------- scoring ----------

class ScoreCreate(BaseModel):
    criterion: str = Field(min_length=1, max_length=100)
    value: float = Field(ge=0, le=10)


class ScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    submission_id: str
    judge_id: str
    criterion: str
    value: float


# ---------- leaderboard ----------

class LeaderboardRow(BaseModel):
    team_id: str
    team_name: str
    submission_id: str
    submission_title: str
    status: SubmissionStatus
    total_score: float
    average_score: float
    score_count: int
    rank: int
