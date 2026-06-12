"""Type-aware planning drafts (S7.6): the AI agenda-draft, specialised per type.

Each event type has a milestone template — the checklist its organiser actually
needs. A hackathon drafts a judging schedule, a webinar a promo timeline, a
workshop a session plan, a conference a run-of-show. Every milestone is scored
for relevance against a free-text theme (reusing the keyless S3 embedder) and
scheduled to a concrete target time across the event's window (or its lead-up,
for promo-style plans). No new keys, no Event-model fork.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.embedding import Embedder, cosine, default_embedder
from app.models.event import EventType
from app.services.event_service import EventService


@dataclass(frozen=True)
class Milestone:
    """One template step: a key, a label, and the text used for scoring."""

    key: str
    label: str
    detail: str


@dataclass(frozen=True)
class PlanItem:
    """A scheduled, theme-scored milestone in a drafted plan."""

    order: int
    key: str
    label: str
    detail: str
    target_at: datetime
    relevance: float


# Per-type milestone templates. Order is the natural sequence of the plan.
_TEMPLATES: dict[EventType, list[Milestone]] = {
    EventType.HACKATHON: [
        Milestone("registration", "Open registration", "participant signups teams forming"),
        Milestone("kickoff", "Kickoff & team formation", "opening ceremony team building rules"),
        Milestone("build", "Build sprint", "hacking coding building prototype development"),
        Milestone("submit", "Submission deadline", "project submission repo demo upload"),
        Milestone("judging", "Judging & scoring", "judges scoring rubric evaluation review"),
        Milestone("awards", "Awards ceremony", "winners prizes leaderboard announcement"),
    ],
    EventType.WEBINAR: [
        Milestone("announce", "Announce the webinar", "announcement landing page registration open"),
        Milestone("promo", "Promotion push", "marketing social email promotion campaign"),
        Milestone("reminders", "Send reminders", "reminder email schedule attendees"),
        Milestone("dryrun", "Tech dry-run", "rehearsal streaming setup audio video check"),
        Milestone("golive", "Go live", "broadcast live stream presentation"),
        Milestone("followup", "Follow-up & recording", "recording follow-up thank you survey"),
    ],
    EventType.WORKSHOP: [
        Milestone("prereqs", "Publish prerequisites", "prerequisites requirements prep reading"),
        Milestone("materials", "Prepare materials", "materials handouts exercises resources"),
        Milestone("setup", "Setup & check-in", "room setup environment check-in seating"),
        Milestone("run", "Run the workshop", "hands-on instruction exercises facilitation"),
        Milestone("feedback", "Collect feedback", "feedback survey retrospective improvement"),
    ],
}

# Conference / meetup / hybrid and anything else fall back to a generic plan.
_DEFAULT_TEMPLATE: list[Milestone] = [
    Milestone("cfp", "Call for proposals", "call for papers speakers submissions"),
    Milestone("schedule", "Build the schedule", "agenda tracks rooms scheduling speakers"),
    Milestone("runofshow", "Run-of-show", "run of show logistics stage management"),
    Milestone("wrap", "Wrap-up & recordings", "wrap up recordings thank you survey"),
]


def template_for(event_type: EventType) -> list[Milestone]:
    """The milestone template for an event type (generic fallback if untyped)."""
    return _TEMPLATES.get(event_type, _DEFAULT_TEMPLATE)


class PlanService:
    def __init__(
        self, session: AsyncSession, embedder: Embedder | None = None
    ) -> None:
        self.session = session
        self.events = EventService(session)
        self.embed: Embedder = embedder or default_embedder()

    async def draft_plan(
        self, event_id: str, theme: str, tenant_id: str | None
    ) -> list[PlanItem]:
        """Draft a type-aware plan: scored + scheduled milestones for an event."""
        event = await self.events.get_event(event_id, tenant_id)
        template = template_for(event.event_type)
        theme_vec = self.embed(theme) if theme else None

        targets = _schedule(event.event_type, event.starts_at, event.ends_at, len(template))
        items: list[PlanItem] = []
        for order, (m, target) in enumerate(zip(template, targets)):
            relevance = (
                cosine(theme_vec, self.embed(f"{m.label} {m.detail}"))
                if theme_vec is not None
                else 0.0
            )
            items.append(
                PlanItem(
                    order=order,
                    key=m.key,
                    label=m.label,
                    detail=m.detail,
                    target_at=target,
                    relevance=relevance,
                )
            )
        return items


def _schedule(
    event_type: EventType, starts_at: datetime, ends_at: datetime, count: int
) -> list[datetime]:
    """Even target times for the milestones.

    Webinars are promo-led, so their plan runs across the *lead-up* window (the
    two weeks before the event, ending at the start). Every other type spreads
    its milestones across the event window itself.
    """
    if count <= 0:
        return []
    if event_type is EventType.WEBINAR:
        window_start = starts_at - timedelta(days=14)
        window_end = starts_at
    else:
        window_start = starts_at
        window_end = ends_at
    span = (window_end - window_start) / max(count - 1, 1)
    return [window_start + span * i for i in range(count)]
