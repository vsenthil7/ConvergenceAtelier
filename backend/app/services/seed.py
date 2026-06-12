"""Idempotent demo data seeder.

Creates a platform super-admin, two tenants each with a tenant-admin, a regular
user, and a sample event with agenda sessions. Safe to run repeatedly: it checks
for the super-admin and bails if seeding already happened.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.event import Event, EventType, Session, SessionMode
from app.models.hackathon import Score, Submission, SubmissionStatus, Team, TeamMember
from app.models.identity import Role, Tenant, User

DEMO_PASSWORD = "Atelier!2026"  # noqa: S105 — demo-only credential, documented.


async def seed_demo(session: AsyncSession) -> bool:
    """Seed demo data. Returns True if it seeded, False if already present."""
    existing = await session.execute(
        select(User).where(User.email == "super@atelier.demo")
    )
    if existing.scalar_one_or_none() is not None:
        return False

    pw = hash_password(DEMO_PASSWORD)
    now = datetime.now(timezone.utc)

    super_admin = User(
        email="super@atelier.demo",
        full_name="Platform Owner",
        password_hash=pw,
        role=Role.SUPER_ADMIN,
        tenant_id=None,
        auth_provider="local",
    )
    session.add(super_admin)

    # Remember the first tenant + its attendee so we can attach a demo hackathon.
    first_tenant_id: str | None = None
    first_user_id: str | None = None

    specs = [
        ("React Summit Org", "react-summit", "Amsterdam"),
        ("Vue Conf Org", "vue-conf", "Berlin"),
    ]
    for name, slug, city in specs:
        tenant = Tenant(name=name, slug=slug)
        session.add(tenant)
        await session.flush()  # get tenant.id
        if first_tenant_id is None:
            first_tenant_id = tenant.id

        session.add(
            User(
                email=f"admin@{slug}.demo",
                full_name=f"{name} Admin",
                password_hash=pw,
                role=Role.TENANT_ADMIN,
                tenant_id=tenant.id,
                auth_provider="local",
            )
        )
        attendee = User(
            email=f"user@{slug}.demo",
            full_name=f"{name} Attendee",
            password_hash=pw,
            role=Role.USER,
            tenant_id=tenant.id,
            auth_provider="local",
        )
        session.add(attendee)
        await session.flush()
        if first_user_id is None:
            first_user_id = attendee.id

        event = Event(
            tenant_id=tenant.id,
            name=f"{name} 2026",
            location=city,
            description=f"The flagship {name} conference.",
            starts_at=now + timedelta(days=30),
            ends_at=now + timedelta(days=31),
        )
        session.add(event)
        await session.flush()

        # Sessions are scheduled ON the event's opening day at fixed clock hours
        # (09:00–15:00), so the Scheduler — which opens on the event start date at
        # the start of the working day — shows them in the default viewport.
        # Mode + media URLs demo the S7.2 online / hybrid / recording features.
        day = event.starts_at.replace(hour=9, minute=0, second=0, microsecond=0)
        agenda = [
            ("Opening Keynote", "Main", "Jane Developer", 0, 1, SessionMode.HYBRID,
             "https://stream.demo/keynote", "https://rec.demo/keynote"),
            ("State of the Framework", "Main", "John Maintainer", 1, 2, SessionMode.IN_PERSON,
             "", "https://rec.demo/state"),
            ("Performance Deep Dive", "Performance", "Ada Speed", 2, 3, SessionMode.IN_PERSON,
             "", ""),
            ("Testing at Scale", "Quality", "Sam Tester", 3, 4, SessionMode.ONLINE,
             "https://stream.demo/testing", ""),
            ("Accessibility Patterns", "Quality", "Lee A11y", 4, 5, SessionMode.IN_PERSON,
             "", "https://rec.demo/a11y"),
            ("Closing Panel: The Road Ahead", "Main", "Community Panel", 5, 6, SessionMode.HYBRID,
             "https://stream.demo/panel", ""),
        ]
        for title, track, speaker, start_h, end_h, mode, stream, rec in agenda:
            session.add(
                Session(
                    event_id=event.id,
                    title=title,
                    track=track,
                    speaker=speaker,
                    mode=mode,
                    stream_url=stream,
                    recording_url=rec,
                    starts_at=day + timedelta(hours=start_h),
                    ends_at=day + timedelta(hours=end_h),
                )
            )

    # --- demo hackathon (S7.3): a typed event with teams, submissions, scores ---
    if first_tenant_id is not None and first_user_id is not None:
        await _seed_hackathon(session, first_tenant_id, first_user_id, super_admin, now)

    await session.commit()
    return True


async def _seed_hackathon(
    session: AsyncSession,
    tenant_id: str,
    attendee_id: str,
    judge: User,
    now: datetime,
) -> None:
    """Seed one hackathon event with two teams, submissions, and judge scores so
    the hackathon panel + live leaderboard are populated in the demo."""
    hack = Event(
        tenant_id=tenant_id,
        name="React Summit Hack 2026",
        location="Amsterdam",
        description="48-hour build sprint: ship something delightful.",
        event_type=EventType.HACKATHON,
        config={"judging_opens": "15:00", "max_team_size": 5},
        starts_at=now + timedelta(days=20),
        ends_at=now + timedelta(days=22),
    )
    session.add(hack)
    await session.flush()

    # Two teams, each with the demo attendee as a member of the first.
    falcons = Team(event_id=hack.id, name="Falcons")
    eagles = Team(event_id=hack.id, name="Eagles")
    session.add_all([falcons, eagles])
    await session.flush()
    session.add(TeamMember(team_id=falcons.id, user_id=attendee_id))

    chrono = Submission(
        team_id=falcons.id,
        title="ChronoSync",
        summary="Real-time agenda sync across devices.",
        repo_url="https://github.com/demo/chronosync",
        demo_url="https://demo.example/chronosync",
        status=SubmissionStatus.SUBMITTED,
    )
    nimbus = Submission(
        team_id=eagles.id,
        title="Nimbus",
        summary="AI matchmaking for hallway tracks.",
        repo_url="https://github.com/demo/nimbus",
        demo_url="https://demo.example/nimbus",
        status=SubmissionStatus.SUBMITTED,
    )
    session.add_all([chrono, nimbus])
    await session.flush()

    # Judge scores: Nimbus edges ahead overall.
    session.add_all(
        [
            Score(submission_id=chrono.id, judge_id=judge.id, criterion="impact", value=7.0),
            Score(submission_id=chrono.id, judge_id=judge.id, criterion="tech", value=8.0),
            Score(submission_id=nimbus.id, judge_id=judge.id, criterion="impact", value=9.0),
            Score(submission_id=nimbus.id, judge_id=judge.id, criterion="tech", value=8.0),
        ]
    )
