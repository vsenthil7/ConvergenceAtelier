"""Hackathon module API tests (S7.3): teams, submissions, scoring, leaderboard.

Covers functional happy paths, RBAC negatives, tenant isolation, and the
leaderboard ranking maths.
"""
from __future__ import annotations

from app.models.identity import Role
from tests.conftest import bearer, make_event


def _admin1(ids):
    return bearer(ids["a1"], Role.TENANT_ADMIN, ids["t1"])


def _user1(ids):
    return bearer(ids["u1"], Role.USER, ids["t1"])


def _admin2(ids):
    return bearer(ids["a2"], Role.TENANT_ADMIN, ids["t2"])


# ---------- teams ----------

async def test_team_crud_and_join(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await make_event(maker, ids["t1"], "Hack")
    async with make_client(maker, _user1(ids)) as c:
        created = await c.post(f"/api/events/{eid}/hackathon/teams", json={"name": "Falcons"})
        assert created.status_code == 201
        team_id = created.json()["id"]
        # join the team
        joined = await c.post(f"/api/events/{eid}/hackathon/teams/{team_id}/join")
        assert joined.status_code == 200
        assert len(joined.json()["members"]) == 1
        assert joined.json()["members"][0]["email"] == "u1@x.com"
        # listing shows the team
        teams = await c.get(f"/api/events/{eid}/hackathon/teams")
        assert teams.status_code == 200
        assert len(teams.json()) == 1


async def test_join_is_idempotent(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await make_event(maker, ids["t1"], "Hack")
    async with make_client(maker, _user1(ids)) as c:
        team_id = (await c.post(f"/api/events/{eid}/hackathon/teams", json={"name": "T"})).json()["id"]
        await c.post(f"/api/events/{eid}/hackathon/teams/{team_id}/join")
        again = await c.post(f"/api/events/{eid}/hackathon/teams/{team_id}/join")
        assert again.status_code == 200
        assert len(again.json()["members"]) == 1  # not duplicated


async def test_duplicate_team_name_conflict(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await make_event(maker, ids["t1"], "Hack")
    async with make_client(maker, _user1(ids)) as c:
        await c.post(f"/api/events/{eid}/hackathon/teams", json={"name": "Dup"})
        again = await c.post(f"/api/events/{eid}/hackathon/teams", json={"name": "Dup"})
    assert again.status_code == 409


async def test_teams_require_auth(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await make_event(maker, ids["t1"], "Hack")
    async with make_client(maker) as c:
        assert (await c.get(f"/api/events/{eid}/hackathon/teams")).status_code == 401


async def test_team_tenant_isolation(make_client, seeded):
    """A t1 user cannot create a team on a t2 event (event out of scope)."""
    maker, ids = seeded["maker"], seeded["ids"]
    other = await make_event(maker, ids["t2"], "OtherHack")
    async with make_client(maker, _user1(ids)) as c:
        resp = await c.post(f"/api/events/{other}/hackathon/teams", json={"name": "X"})
    assert resp.status_code == 404


async def test_join_unknown_team_404(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await make_event(maker, ids["t1"], "Hack")
    async with make_client(maker, _user1(ids)) as c:
        assert (await c.post(f"/api/events/{eid}/hackathon/teams/nope/join")).status_code == 404


# ---------- submissions ----------

async def test_submission_create_and_update(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await make_event(maker, ids["t1"], "Hack")
    async with make_client(maker, _user1(ids)) as c:
        team_id = (await c.post(f"/api/events/{eid}/hackathon/teams", json={"name": "T"})).json()["id"]
        sub = await c.post(
            f"/api/events/{eid}/hackathon/teams/{team_id}/submission",
            json={
                "title": "ChronoSync",
                "summary": "A time tool",
                "repo_url": "https://github.com/x/y",
                "demo_url": "https://demo.x/y",
            },
        )
        assert sub.status_code == 201
        assert sub.json()["status"] == "draft"
        sub_id = sub.json()["id"]
        # mark it submitted
        patched = await c.patch(
            f"/api/events/{eid}/hackathon/submissions/{sub_id}",
            json={"status": "submitted", "summary": "A better time tool"},
        )
        assert patched.status_code == 200
        assert patched.json()["status"] == "submitted"
        assert patched.json()["summary"] == "A better time tool"


async def test_one_submission_per_team_conflict(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await make_event(maker, ids["t1"], "Hack")
    async with make_client(maker, _user1(ids)) as c:
        team_id = (await c.post(f"/api/events/{eid}/hackathon/teams", json={"name": "T"})).json()["id"]
        await c.post(f"/api/events/{eid}/hackathon/teams/{team_id}/submission", json={"title": "One"})
        again = await c.post(
            f"/api/events/{eid}/hackathon/teams/{team_id}/submission", json={"title": "Two"}
        )
    assert again.status_code == 409


async def test_submission_on_unknown_team_404(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await make_event(maker, ids["t1"], "Hack")
    async with make_client(maker, _user1(ids)) as c:
        resp = await c.post(
            f"/api/events/{eid}/hackathon/teams/ghost/submission", json={"title": "X"}
        )
    assert resp.status_code == 404


async def test_list_submissions(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await make_event(maker, ids["t1"], "Hack")
    async with make_client(maker, _user1(ids)) as c:
        t1 = (await c.post(f"/api/events/{eid}/hackathon/teams", json={"name": "A"})).json()["id"]
        t2 = (await c.post(f"/api/events/{eid}/hackathon/teams", json={"name": "B"})).json()["id"]
        await c.post(f"/api/events/{eid}/hackathon/teams/{t1}/submission", json={"title": "Alpha"})
        await c.post(f"/api/events/{eid}/hackathon/teams/{t2}/submission", json={"title": "Beta"})
        subs = await c.get(f"/api/events/{eid}/hackathon/submissions")
    assert subs.status_code == 200
    assert [s["title"] for s in subs.json()] == ["Alpha", "Beta"]


# ---------- scoring + leaderboard ----------

async def _setup_two_submissions(c, eid):
    t1 = (await c.post(f"/api/events/{eid}/hackathon/teams", json={"name": "A"})).json()["id"]
    t2 = (await c.post(f"/api/events/{eid}/hackathon/teams", json={"name": "B"})).json()["id"]
    s1 = (await c.post(f"/api/events/{eid}/hackathon/teams/{t1}/submission", json={"title": "Alpha"})).json()["id"]
    s2 = (await c.post(f"/api/events/{eid}/hackathon/teams/{t2}/submission", json={"title": "Beta"})).json()["id"]
    return s1, s2


async def test_admin_scores_and_leaderboard_ranks(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await make_event(maker, ids["t1"], "Hack")
    async with make_client(maker, _user1(ids)) as c:
        s1, s2 = await _setup_two_submissions(c, eid)
    async with make_client(maker, _admin1(ids)) as judge:
        # Beta scores higher overall
        await judge.post(f"/api/events/{eid}/hackathon/submissions/{s1}/scores", json={"criterion": "impact", "value": 5})
        await judge.post(f"/api/events/{eid}/hackathon/submissions/{s1}/scores", json={"criterion": "tech", "value": 4})
        await judge.post(f"/api/events/{eid}/hackathon/submissions/{s2}/scores", json={"criterion": "impact", "value": 9})
        await judge.post(f"/api/events/{eid}/hackathon/submissions/{s2}/scores", json={"criterion": "tech", "value": 8})
        board = await judge.get(f"/api/events/{eid}/hackathon/leaderboard")
    assert board.status_code == 200
    rows = board.json()
    assert rows[0]["submission_title"] == "Beta"
    assert rows[0]["rank"] == 1
    assert rows[0]["total_score"] == 17
    assert rows[1]["submission_title"] == "Alpha"
    assert rows[1]["rank"] == 2
    assert rows[1]["total_score"] == 9


async def test_rescore_updates_in_place(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await make_event(maker, ids["t1"], "Hack")
    async with make_client(maker, _user1(ids)) as c:
        s1, _ = await _setup_two_submissions(c, eid)
    async with make_client(maker, _admin1(ids)) as judge:
        await judge.post(f"/api/events/{eid}/hackathon/submissions/{s1}/scores", json={"criterion": "impact", "value": 3})
        await judge.post(f"/api/events/{eid}/hackathon/submissions/{s1}/scores", json={"criterion": "impact", "value": 7})
        board = await judge.get(f"/api/events/{eid}/hackathon/leaderboard")
    alpha = next(r for r in board.json() if r["submission_title"] == "Alpha")
    assert alpha["total_score"] == 7  # not 3+7
    assert alpha["score_count"] == 1


async def test_user_cannot_score_403(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await make_event(maker, ids["t1"], "Hack")
    async with make_client(maker, _user1(ids)) as c:
        s1, _ = await _setup_two_submissions(c, eid)
        resp = await c.post(
            f"/api/events/{eid}/hackathon/submissions/{s1}/scores",
            json={"criterion": "impact", "value": 5},
        )
    assert resp.status_code == 403


async def test_score_out_of_range_422(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await make_event(maker, ids["t1"], "Hack")
    async with make_client(maker, _user1(ids)) as c:
        s1, _ = await _setup_two_submissions(c, eid)
    async with make_client(maker, _admin1(ids)) as judge:
        resp = await judge.post(
            f"/api/events/{eid}/hackathon/submissions/{s1}/scores",
            json={"criterion": "impact", "value": 99},
        )
    assert resp.status_code == 422


async def test_leaderboard_unscored_zero(make_client, seeded):
    maker, ids = seeded["maker"], seeded["ids"]
    eid = await make_event(maker, ids["t1"], "Hack")
    async with make_client(maker, _user1(ids)) as c:
        await _setup_two_submissions(c, eid)
        board = await c.get(f"/api/events/{eid}/hackathon/leaderboard")
    rows = board.json()
    assert all(r["total_score"] == 0 for r in rows)
    assert all(r["score_count"] == 0 for r in rows)
    # stable order by title when all zero
    assert [r["submission_title"] for r in rows] == ["Alpha", "Beta"]
