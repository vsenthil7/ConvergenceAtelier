"""AI discovery: semantic talk recommendations + matchmaking (S3).

Built on the injectable embedder in ``app.core.embedding`` so the whole feature
runs keyless in demo mode and swaps to a real provider with one constructor arg.
All reads go through ``EventService`` so tenant scoping + role rules are reused.

Three capabilities:
  * ``recommend_for_session`` — given a session, the most semantically similar
    other sessions (across the tenant's events).
  * ``recommend_for_interests`` — given a free-text interest profile, the best
    matching sessions.
  * ``match_attendees`` — pair attendees by interest-profile similarity.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.embedding import Embedder, cosine, default_embedder
from app.models.event import Session as AgendaSession
from app.services.errors import NotFoundError
from app.services.event_service import EventService


@dataclass(frozen=True)
class ScoredSession:
    """A session paired with its similarity score (0..1)."""

    session: AgendaSession
    score: float


@dataclass(frozen=True)
class AttendeeProfile:
    """Minimal attendee profile for matchmaking (id + free-text interests)."""

    id: str
    name: str
    interests: str


@dataclass(frozen=True)
class AttendeeMatch:
    """A pair of attendees with their interest-similarity score."""

    a: AttendeeProfile
    b: AttendeeProfile
    score: float


@dataclass(frozen=True)
class AgendaSlot:
    """A session placed in a suggested running order with a rationale."""

    order: int
    session: AgendaSession
    relevance: float
    track: str


def _session_text(s: AgendaSession) -> str:
    """The text used to represent a session for embedding."""
    return f"{s.title} {s.track} {s.speaker}"


class DiscoveryService:
    def __init__(
        self, session: AsyncSession, embedder: Embedder | None = None
    ) -> None:
        self.session = session
        self.events = EventService(session)
        self.embed: Embedder = embedder or default_embedder()

    async def _all_sessions(self, tenant_id: str | None) -> list[AgendaSession]:
        events = await self.events.list_events(tenant_id)
        sessions: list[AgendaSession] = []
        for event in events:
            sessions.extend(event.sessions)
        return sessions

    async def _find_session(
        self, session_id: str, tenant_id: str | None
    ) -> tuple[AgendaSession, list[AgendaSession]]:
        sessions = await self._all_sessions(tenant_id)
        target = next((s for s in sessions if s.id == session_id), None)
        if target is None:
            raise NotFoundError("Session", session_id)
        return target, sessions

    def _rank(
        self, query_vec: list[float], candidates: list[AgendaSession], limit: int
    ) -> list[ScoredSession]:
        scored = [
            ScoredSession(session=c, score=cosine(query_vec, self.embed(_session_text(c))))
            for c in candidates
        ]
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:limit]

    async def recommend_for_session(
        self, session_id: str, tenant_id: str | None, limit: int = 5
    ) -> list[ScoredSession]:
        """Sessions most similar to the given one (excluding itself)."""
        target, sessions = await self._find_session(session_id, tenant_id)
        others = [s for s in sessions if s.id != session_id]
        query_vec = self.embed(_session_text(target))
        return self._rank(query_vec, others, limit)

    async def recommend_for_interests(
        self, interests: str, tenant_id: str | None, limit: int = 5
    ) -> list[ScoredSession]:
        """Sessions best matching a free-text interest profile."""
        sessions = await self._all_sessions(tenant_id)
        query_vec = self.embed(interests)
        return self._rank(query_vec, sessions, limit)

    async def recommend_across_links(
        self,
        event_id: str,
        interests: str,
        tenant_id: str | None,
        limit: int = 5,
    ) -> list[ScoredSession]:
        """Recommend sessions across an event AND its linked events (S7.5).

        Discovery for a linked series: gather the sessions of the event plus
        every event linked to it, then rank against the interest profile. Reuses
        the same embedder, so it stays keyless in demo mode.
        """
        # Imported here to avoid a circular import at module load.
        from app.services.link_service import LinkService

        links = LinkService(self.session)
        event = await self.events.get_event(event_id, tenant_id)
        linked = await links.linked_events(event_id, tenant_id)
        sessions: list[AgendaSession] = list(event.sessions)
        # Re-fetch each linked event through get_event so its sessions are eagerly
        # loaded (linked_events does not eager-load the sessions relationship).
        for ev in linked:
            full = await self.events.get_event(ev.id, tenant_id)
            sessions.extend(full.sessions)
        query_vec = self.embed(interests)
        return self._rank(query_vec, sessions, limit)

    def match_attendees(
        self, attendees: list[AttendeeProfile], limit: int = 5
    ) -> list[AttendeeMatch]:
        """Rank attendee pairs by interest-profile similarity (descending).

        Pure/synchronous: matchmaking is over the supplied profiles, so it needs
        no DB round-trip and is trivially testable.
        """
        vectors = {a.id: self.embed(a.interests) for a in attendees}
        matches: list[AttendeeMatch] = []
        for i in range(len(attendees)):
            for j in range(i + 1, len(attendees)):
                a, b = attendees[i], attendees[j]
                matches.append(
                    AttendeeMatch(a=a, b=b, score=cosine(vectors[a.id], vectors[b.id]))
                )
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:limit]

    async def draft_agenda(
        self, event_id: str, theme: str, tenant_id: str | None
    ) -> list[AgendaSlot]:
        """Suggest a running order for an event's sessions around a theme.

        Deterministic "AI draft": score every session against the theme, then
        group by track (keeping each track's talks together) and order the
        tracks by their best in-track relevance, so the most on-theme track
        opens the day. Within a track, talks are ordered by relevance.
        Runs keyless via the local embedder.
        """
        event = await self.events.get_event(event_id, tenant_id)
        theme_vec = self.embed(theme)
        scored = [
            (s, cosine(theme_vec, self.embed(_session_text(s))))
            for s in event.sessions
        ]
        # Best relevance per track decides track order; descending.
        track_best: dict[str, float] = {}
        for s, rel in scored:
            track_best[s.track] = max(track_best.get(s.track, 0.0), rel)
        ordered_tracks = sorted(track_best, key=lambda t: track_best[t], reverse=True)

        slots: list[AgendaSlot] = []
        order = 0
        for track in ordered_tracks:
            in_track = sorted(
                [(s, rel) for s, rel in scored if s.track == track],
                key=lambda pair: pair[1],
                reverse=True,
            )
            for s, rel in in_track:
                slots.append(
                    AgendaSlot(order=order, session=s, relevance=rel, track=track)
                )
                order += 1
        return slots
