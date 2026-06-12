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
from app.models.event import Event, Session
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

        # Sessions are scheduled ON the event's opening day (not relative to now),
        # so the Scheduler — which opens on the event start date — shows them.
        day = event.starts_at
        agenda = [
            ("Opening Keynote", "Main", "Jane Developer", 1, 2),
            ("State of the Framework", "Main", "John Maintainer", 2, 3),
            ("Performance Deep Dive", "Performance", "Ada Speed", 3, 4),
            ("Testing at Scale", "Quality", "Sam Tester", 4, 5),
            ("Accessibility Patterns", "Quality", "Lee A11y", 5, 6),
            ("Closing Panel: The Road Ahead", "Main", "Community Panel", 6, 7),
        ]
        for title, track, speaker, start_h, end_h in agenda:
            session.add(
                Session(
                    event_id=event.id,
                    title=title,
                    track=track,
                    speaker=speaker,
                    starts_at=day + timedelta(hours=start_h),
                    ends_at=day + timedelta(hours=end_h),
                )
            )

    await session.commit()
    return True
