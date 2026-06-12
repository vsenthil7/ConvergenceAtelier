"""Direct PlanService tests (S7.6): per-type templates, scheduling, scoring."""
from __future__ import annotations

from datetime import datetime, timezone

from app.models.event import Event, EventType
from app.services.plan_service import PlanService, template_for, _schedule


async def _typed_event(maker, tenant_id, event_type, days=2):
    async with maker() as s:
        e = Event(
            tenant_id=tenant_id,
            name=f"{event_type.value} event",
            event_type=event_type,
            starts_at=datetime(2026, 7, 1, 9, tzinfo=timezone.utc),
            ends_at=datetime(2026, 7, 1 + days, 17, tzinfo=timezone.utc),
        )
        s.add(e)
        await s.commit()
        await s.refresh(e)
        return e


def test_template_for_each_type_distinct():
    hack = [m.key for m in template_for(EventType.HACKATHON)]
    web = [m.key for m in template_for(EventType.WEBINAR)]
    work = [m.key for m in template_for(EventType.WORKSHOP)]
    default = [m.key for m in template_for(EventType.CONFERENCE)]
    assert hack[0] == "registration" and "judging" in hack
    assert web[0] == "announce" and "golive" in web
    assert work[0] == "prereqs" and "feedback" in work
    assert default[0] == "cfp" and "wrap" in default
    # meetup/hybrid fall back to the default template
    assert [m.key for m in template_for(EventType.MEETUP)] == default
    assert [m.key for m in template_for(EventType.HYBRID)] == default


def test_schedule_empty_for_zero_count():
    """Defensive guard: no milestones -> no target times."""
    start = datetime(2026, 7, 1, 9, tzinfo=timezone.utc)
    end = datetime(2026, 7, 2, 17, tzinfo=timezone.utc)
    assert _schedule(EventType.CONFERENCE, start, end, 0) == []


async def test_hackathon_plan_is_judging_schedule(seeded):
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    e = await _typed_event(maker, t1, EventType.HACKATHON)
    async with maker() as s:
        plan = await PlanService(s).draft_plan(e.id, "judging and scoring", t1)
    keys = [p.key for p in plan]
    assert keys == ["registration", "kickoff", "build", "submit", "judging", "awards"]
    # ordered, and milestones fall within the event window
    assert [p.order for p in plan] == list(range(len(plan)))
    assert plan[0].target_at == e.starts_at
    assert plan[-1].target_at == e.ends_at
    # a judging-themed query scores the judging milestone above registration
    by_key = {p.key: p.relevance for p in plan}
    assert by_key["judging"] > by_key["registration"]


async def test_webinar_plan_runs_in_lead_up_window(seeded):
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    e = await _typed_event(maker, t1, EventType.WEBINAR)
    async with maker() as s:
        plan = await PlanService(s).draft_plan(e.id, "promotion", t1)
    assert [p.key for p in plan][0] == "announce"
    # promo plan schedules BEFORE the event starts, ending at the start time
    assert plan[0].target_at < e.starts_at
    assert plan[-1].target_at == e.starts_at


async def test_default_plan_for_conference(seeded):
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    e = await _typed_event(maker, t1, EventType.CONFERENCE)
    async with maker() as s:
        plan = await PlanService(s).draft_plan(e.id, "", t1)
    assert [p.key for p in plan] == ["cfp", "schedule", "runofshow", "wrap"]
    # empty theme → relevance defaults to 0 for every item
    assert all(p.relevance == 0.0 for p in plan)


async def test_workshop_plan_scored_against_theme(seeded):
    maker, t1 = seeded["maker"], seeded["ids"]["t1"]
    e = await _typed_event(maker, t1, EventType.WORKSHOP)
    async with maker() as s:
        plan = await PlanService(s).draft_plan(e.id, "hands-on exercises", t1)
    by_key = {p.key: p.relevance for p in plan}
    assert by_key["run"] >= 0.0
    # at least one milestone scores positively for a matching theme
    assert any(p.relevance > 0.0 for p in plan)
