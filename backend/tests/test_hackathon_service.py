"""Direct HackathonService tests (deterministic, no ASGI) — also closes coverage
on service branches the transport doesn't trace."""
from __future__ import annotations

import pytest

from app.models.identity import Role, User
from app.models.hackathon import SubmissionStatus
from app.schemas.hackathon import SubmissionCreate, SubmissionUpdate, TeamCreate
from app.services.errors import ConflictError, NotFoundError
from app.services.hackathon_service import HackathonService
from tests.conftest import make_event


async def _user(maker, tenant_id, email="m@x.com"):
    async with maker() as s:
        u = User(email=email, role=Role.USER, tenant_id=tenant_id)
        s.add(u)
        await s.commit()
        await s.refresh(u)
        return u


async def test_join_persists_member(seeded):
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    eid = await make_event(maker, t1, "Hack")
    user = await _user(maker, t1)
    async with maker() as s:
        svc = HackathonService(s)
        team = await svc.create_team(eid, t1, TeamCreate(name="Falcons"))
    async with maker() as s:
        svc = HackathonService(s)
        joined = await svc.join_team(eid, team.id, user, t1)
        assert len(joined.members) == 1
        assert joined.members[0].user.email == "m@x.com"


async def test_create_team_duplicate_raises(seeded):
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    eid = await make_event(maker, t1, "Hack")
    async with maker() as s:
        svc = HackathonService(s)
        await svc.create_team(eid, t1, TeamCreate(name="Dup"))
        with pytest.raises(ConflictError):
            await svc.create_team(eid, t1, TeamCreate(name="Dup"))


async def test_join_wrong_event_team_raises(seeded):
    maker = seeded["maker"]
    t1, t2 = seeded["ids"]["t1"], seeded["ids"]["t2"]
    e1 = await make_event(maker, t1, "H1")
    e2 = await make_event(maker, t2, "H2")
    user = await _user(maker, t1)
    async with maker() as s:
        svc = HackathonService(s)
        team = await svc.create_team(e2, t2, TeamCreate(name="T"))
    # team belongs to e2; joining via e1 (in scope for t1) must 404 on team match
    async with maker() as s:
        svc = HackathonService(s)
        with pytest.raises(NotFoundError):
            await svc.join_team(e1, team.id, user, t1)


async def test_submission_on_mismatched_event_raises(seeded):
    maker = seeded["maker"]
    t1, t2 = seeded["ids"]["t1"], seeded["ids"]["t2"]
    e1 = await make_event(maker, t1, "H1")
    e2 = await make_event(maker, t2, "H2")
    async with maker() as s:
        svc = HackathonService(s)
        team = await svc.create_team(e2, t2, TeamCreate(name="T"))
    async with maker() as s:
        svc = HackathonService(s)
        with pytest.raises(NotFoundError):
            await svc.create_submission(e1, team.id, t1, SubmissionCreate(title="X"))


async def test_update_unknown_submission_raises(seeded):
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    eid = await make_event(maker, t1, "Hack")
    async with maker() as s:
        svc = HackathonService(s)
        with pytest.raises(NotFoundError):
            await svc.update_submission(eid, "ghost", t1, SubmissionUpdate(title="X"))


async def test_record_score_unknown_submission_raises(seeded):
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    eid = await make_event(maker, t1, "Hack")
    judge = await _user(maker, t1, "judge@x.com")
    async with maker() as s:
        svc = HackathonService(s)
        with pytest.raises(NotFoundError):
            await svc.record_score(eid, "ghost", judge, t1, "impact", 5.0)


async def test_update_submission_ignores_explicit_none(seeded):
    """A partial update passing status=None must not blank the NOT NULL column."""
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    eid = await make_event(maker, t1, "Hack")
    async with maker() as s:
        svc = HackathonService(s)
        team = await svc.create_team(eid, t1, TeamCreate(name="T"))
        sub = await svc.create_submission(eid, team.id, t1, SubmissionCreate(title="A"))
    async with maker() as s:
        svc = HackathonService(s)
        updated = await svc.update_submission(
            eid, sub.id, t1, SubmissionUpdate(status=None, repo_url="https://r/x")
        )
        assert updated.status == SubmissionStatus.DRAFT  # unchanged
        assert updated.repo_url == "https://r/x"


async def test_leaderboard_full_compute_and_ranking(seeded):
    """Two scored submissions: verify totals, averages, counts, and ranks."""
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    eid = await make_event(maker, t1, "Hack")
    judge = await _user(maker, t1, "judge2@x.com")
    async with maker() as s:
        svc = HackathonService(s)
        ta = await svc.create_team(eid, t1, TeamCreate(name="A"))
        tb = await svc.create_team(eid, t1, TeamCreate(name="B"))
        sa = await svc.create_submission(eid, ta.id, t1, SubmissionCreate(title="Alpha"))
        sb = await svc.create_submission(eid, tb.id, t1, SubmissionCreate(title="Beta"))
    async with maker() as s:
        svc = HackathonService(s)
        await svc.record_score(eid, sa.id, judge, t1, "impact", 6.0)
        await svc.record_score(eid, sa.id, judge, t1, "tech", 4.0)
        await svc.record_score(eid, sb.id, judge, t1, "impact", 3.0)
        board = await svc.leaderboard(eid, t1)
    top = board[0]
    assert top.submission_title == "Alpha"
    assert top.rank == 1
    assert top.total_score == 10.0
    assert top.average_score == 5.0
    assert top.score_count == 2
    assert board[1].submission_title == "Beta"
    assert board[1].rank == 2
    assert board[1].total_score == 3.0


async def test_get_unknown_team_raises(seeded):
    """_get_team not-found path (via list/join on a ghost id)."""
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    eid = await make_event(maker, t1, "Hack")
    user = await _user(maker, t1)
    async with maker() as s:
        svc = HackathonService(s)
        with pytest.raises(NotFoundError):
            await svc.join_team(eid, "ghost-team", user, t1)


async def test_submission_team_event_mismatch_raises(seeded):
    """create_submission where the team exists but belongs to another event.

    Both events are in the SAME tenant so the event-scope check passes and the
    team genuinely resolves; the guard that fires is the team.event_id mismatch.
    """
    maker = seeded["maker"]
    t1 = seeded["ids"]["t1"]
    e1 = await make_event(maker, t1, "H1")
    e2 = await make_event(maker, t1, "H2")
    async with maker() as s:
        svc = HackathonService(s)
        team = await svc.create_team(e2, t1, TeamCreate(name="T"))
        team_id = team.id
    assert e1 != e2
    async with maker() as s:
        svc = HackathonService(s)
        # sanity: the team resolves fine on its own (so the raise is the mismatch)
        resolved = await svc._get_team(team_id)
        assert resolved.event_id == e2
        with pytest.raises(NotFoundError):
            await svc.create_submission(e1, team_id, t1, SubmissionCreate(title="X"))


async def test_duplicate_submission_per_team_raises(seeded):
    """A team may have only one submission; a second create raises ConflictError."""
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    eid = await make_event(maker, t1, "Hack")
    async with maker() as s:
        svc = HackathonService(s)
        team = await svc.create_team(eid, t1, TeamCreate(name="T"))
        await svc.create_submission(eid, team.id, t1, SubmissionCreate(title="One"))
        with pytest.raises(ConflictError):
            await svc.create_submission(eid, team.id, t1, SubmissionCreate(title="Two"))


async def test_rescore_updates_existing_row(seeded):
    """record_score twice on the same criterion updates in place (else branch)."""
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    eid = await make_event(maker, t1, "Hack")
    judge = await _user(maker, t1, "j3@x.com")
    async with maker() as s:
        svc = HackathonService(s)
        team = await svc.create_team(eid, t1, TeamCreate(name="T"))
        sub = await svc.create_submission(eid, team.id, t1, SubmissionCreate(title="A"))
    async with maker() as s:
        svc = HackathonService(s)
        await svc.record_score(eid, sub.id, judge, t1, "impact", 2.0)
        updated = await svc.record_score(eid, sub.id, judge, t1, "impact", 9.0)
        assert updated.value == 9.0
        board = await svc.leaderboard(eid, t1)
    assert board[0].total_score == 9.0
    assert board[0].score_count == 1
