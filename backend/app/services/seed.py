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
from app.models.event import Event, Session, SessionMode
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

    specs = [
        ("React Summit Org", "react-summit", "Amsterdam"),
        ("Vue Conf Org", "vue-conf", "Berlin"),
    ]
    for name, slug, city in specs:
        tenant = Tenant(name=name, slug=slug)
        session.add(tenant)
        await session.flush()  # get tenant.id

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
        session.add(
            User(
                email=f"user@{slug}.demo",
                full_name=f"{name} Attendee",
                password_hash=pw,
                role=Role.USER,
                tenant_id=tenant.id,
                auth_provider="local",
            )
        )

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

    await session.commit()
    return True
