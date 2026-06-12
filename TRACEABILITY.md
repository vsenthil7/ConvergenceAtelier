# Traceability Matrix — Convergence Atelier

Requirement → Code → Test → Status. Status: ⬜ todo · 🟨 in progress · ✅ done.
A requirement is DONE only when its tests pass at 100% coverage and are pushed.

## Sprint 0 — Scaffold & rails  ✅
backend 8/8 · frontend 7/7 · e2e 8/8 · build OK · `c214b2c`.

## Sprint 1 — Events & agenda CRUD
- Backend ✅ (33 tests, 100%, `d86a379`)
- Frontend ✅ VERIFIED (Grid/Form/Scheduler + tests, 84 frontend tests pass, exit 0)

### S1 frontend requirements
| R1.11 | Typed events client (injectable fetch) | `lib/events.ts` | `events.test.ts` | ✅ |
| R1.12 | Event create/edit form + validation | `components/EventForm.tsx`, `lib/validation.ts` | `EventForm.test.tsx`, `validation.test.ts` | ✅ |
| R1.13 | Events grid (Kendo Grid) | `components/EventsView.tsx` | `EventsView.test.tsx` | ✅ |
| R1.14 | Agenda scheduler view | `components/EventsView.tsx` | `EventsView.test.tsx` | ✅ |
| R1.15 | Empty/error/loading states | `components/EventsView.tsx` | `EventsView.test.tsx` | ✅ |

## Sprint 3 — AI discovery & matchmaking

### Module 3A — Backend: semantic recommendations + matchmaking ✅ VERIFIED (132 tests, 100% cov, exit 0)
| ID | Requirement | Code | Test | Status |
|----|-------------|------|------|--------|
| R3.1 | Deterministic keyless embedding (demo mode) | `core/embedding.py` | `test_embedding.py` | ✅ |
| R3.2 | Cosine similarity + injectable embedder | `core/embedding.py`, `services/discovery_service.py` | `test_embedding.py`, `test_discovery_service.py` | ✅ |
| R3.3 | Session→similar-session recommendations | `services/discovery_service.py`, `api/discovery.py` | `test_discovery_service.py`, `test_discovery_api.py` | ✅ |
| R3.4 | Interest-profile → session recommendations | `services/discovery_service.py`, `api/discovery.py` | `test_discovery_service.py`, `test_discovery_api.py` | ✅ |
| R3.5 | Attendee↔attendee matchmaking | `services/discovery_service.py`, `api/discovery.py` | `test_discovery_service.py`, `test_discovery_api.py` | ✅ |
| R3.6 | Tenant scoping + super-admin span on discovery | `api/discovery.py` | `test_discovery_api.py` | ✅ |
| R3.7 | Auth-gated, all roles (attendee-facing) | `api/discovery.py` | `test_discovery_api.py` | ✅ |
| R3.8 | Real-LLM key behind `use_mocks=false` (config) | `config.py` | `test_api_helpers.py` | ✅ |
| R3.12 | AI agenda draft (theme → ordered, track-grouped running order) | `services/discovery_service.py`, `api/discovery.py` | `test_discovery_service.py`, `test_discovery_api.py` | ✅ |

_Verified via subprocess pytest: 132 passed, 100% coverage, exit 0._
_Embedding is a deterministic bag-of-words hashing vectoriser (256-dim, L2-normalised),_
_so recommendations are reproducible and keyless; a real provider injects with the same_
_`(str)->list[float]` signature. Matchmaking is pure/synchronous over supplied profiles._
_Agenda draft scores each session against the theme, groups by track, and opens with the_
_most on-theme track — a deterministic, explainable "AI draft" running keyless._

### Module 3B — Frontend discovery UI ✅ VERIFIED (105 tests pass, exit 0)
| R3.9 | Typed discovery client (similar/recommend/match/draft) | `lib/discovery.ts` | `discovery.test.ts` | ✅ |
| R3.10 | Discover tab (all roles) + interest search | `App.tsx`, `components/DiscoveryView.tsx` | `App.test.tsx`, `DiscoveryView.test.tsx` | ✅ |
| R3.11 | Ranked results grid with score badges + states | `components/DiscoveryView.tsx` | `DiscoveryView.test.tsx` | ✅ |
| R3.13 | AI agenda-draft UI (event+theme → ordered, track-grouped running order) | `components/DiscoveryView.tsx`, `lib/discovery.ts` | `DiscoveryView.test.tsx`, `discovery.test.ts` | ✅ |
| R3.14 | One-tap demo sign-in (no typing, password never shown) | `components/LoginView.tsx` | `LoginView.test.tsx` | ✅ |

_Verified: 105 vitest tests pass, statements/lines 100%; `discovery.ts` 100% on all metrics._
_R3.14 enhancement: demo accounts are now one-tap buttons that fill the email + seeded_
_password and authenticate; the shared password is never rendered as visible text_
_(asserted by a security test)._

## Sprint 3b — Event registration & participation  🟨  (NEW — closes real product gaps)

Context: prior to S3b a person could only be created by an admin (no self-signup), and
users belonged to a *tenant*, never to an *event* — so there was no "join event", no
per-event attendee roster, and the seeded events had no sessions (blank agenda). S3b
adds the participation layer and fixes the two UX bugs surfaced in review.

| ID | Requirement | Code | Test | Status |
|----|-------------|------|------|--------|
| R3b.1 | Public self-registration (creates `user`; cannot self-grant admin) | `services/auth_service.py`, `api/auth.py`, `schemas/auth.py` | `test_auth_service.py`, `test_registration_api.py`, `test_api_helpers.py` | ✅ |
| R3b.2 | `EventRegistration` model (event↔user, status, unique) + migration | `models/registration.py`, `migrations/versions/a1b2c3d4e5f6_*` | `test_registration_service.py` | ✅ |
| R3b.3 | Register / unregister for an event (attendee self-service) | `services/registration_service.py`, `api/events.py` | `test_registration_service.py`, `test_registration_api.py` | ✅ |
| R3b.4 | Participant roster per event (admin) + my-status (attendee) | `services/registration_service.py`, `api/events.py` | `test_registration_api.py`, `test_api_helpers.py` | ✅ |
| R3b.5 | Tenant isolation + RBAC on registration endpoints | `api/events.py` | `test_registration_api.py` | ✅ |
| R3b.6 | Seed real multi-track sessions ON event day for demo | `services/seed.py` | `test_seed.py` | ✅ |
| R3b.7 | Frontend: self-registration panel on Login | `components/LoginView.tsx`, `lib/auth.ts`, `lib/AuthContext.tsx` | `LoginView.test.tsx`, `auth.test.ts`, `AuthContext.test.tsx` | ✅ |
| R3b.8 | Frontend: event register button + roster on event page | `components/EventsView.tsx`, `lib/events.ts` | `EventsView.test.tsx`, `events.test.ts` | ✅ |
| R3b.9 | Fix: Add-user inline validation (explain disabled state) | `components/UsersView.tsx` | `UsersView.test.tsx` | ✅ |
| R3b.10 | Fix: empty-agenda "no sessions yet" affordance | `components/EventsView.tsx` | `EventsView.test.tsx` | ✅ |

_Backend (R3b.1–R3b.6) VERIFIED: 156 tests, 100% coverage, exit 0 (`41c5ade`). Frontend_
_(R3b.7–R3b.10) VERIFIED: 125 vitest tests, exit 0, statements/lines 100%; prod tsc clean._
_Self-registration provisions a plain attendee in a chosen org; event page shows a_
_Register/Registered✓ toggle for attendees and a participant roster for admins; add-user_
_now explains its disabled state; empty agendas show a "no sessions yet" message._

## Sprint 7 — Event TYPES (product vision, planned)

Goal: make the event a *configurable product* — `Event.event_type` enum + JSON `config`,
with composable feature modules per type over the shared event/session/registration core.
Each row lands GREEN independently with 100% coverage, git-first.

| ID | Requirement | Status |
|----|-------------|--------|
| R7.1 | `event_type` enum + JSON `config` on Event; type-aware create/edit + grid badge + migration | ✅ |
| R7.2 | Session `mode` (in_person/online/hybrid) + `stream_url`/`recording_url`/`meeting_url`; recordings catalog | ✅ |
| R7.2.1 | Session model: mode enum + URL columns + migration | ✅ |
| R7.2.2 | Session schema carries mode + URLs (optional, validated) | ✅ |
| R7.2.3 | Recordings query (sessions with a recording_url) + endpoint | ✅ |
| R7.2.4 | Frontend session/recordings client types + calls | ✅ |
| R7.2.5 | Agenda mode chip + ▶ recording link per talk | ✅ |
| R7.2.6 | "Recordings" catalog panel on the event page | ✅ |
| R7.3 | Hackathon module: Team + Submission (repo/demo links) + judging rubric + leaderboard | ✅ |
| R7.3.1 | `Team` model (event-scoped) + membership + migration | ✅ |
| R7.3.2 | `Submission` model (repo/demo/summary + status enum) + migration | ✅ |
| R7.3.3 | `Score` model (submission × judge × criterion) + migration | ✅ |
| R7.3.4 | HackathonService: teams/join/submit/score + leaderboard compute | ✅ |
| R7.3.5 | REST API `/events/{id}/hackathon/*` with RBAC | ✅ |
| R7.3.6 | Frontend hackathon client types + calls | ✅ |
| R7.3.7 | Hackathon panel on event page (team list + submission form) | ✅ |
| R7.3.8 | Live leaderboard (Kendo Grid) ranked by score | ✅ |
| R7.4 | Webinar module: stream provider + registration cap/waitlist + recording + reminders | ✅ |
| R7.4.1 | `WAITLISTED` registration status + migration | ✅ |
| R7.4.2 | WebinarService: capacity-aware register + waitlist auto-promotion | ✅ |
| R7.4.3 | REST webinar status + admin waitlist endpoints | ✅ |
| R7.4.4 | Reminder schedule from `config.reminders` → absolute send times | ✅ |
| R7.4.5 | Frontend webinar client types + calls | ✅ |
| R7.4.6 | Webinar panel on event page (seat counter + waitlist + stream + reminders) | ✅ |
| R7.4.7 | Seed: demo webinar with capacity, reminders, registrations incl. waitlist | ✅ |
| R7.5 | Linked/hybrid events: event-to-event links + cross-event session catalog | ⬜ |
| R7.6 | Type-aware AI drafts (judging schedule / promo timeline / workshop plan) | ⬜ |

_R7.1 VERIFIED: backend `EventType` enum (conference/hackathon/webinar/meetup/workshop/_
_hybrid) + JSON `config` on Event, type-aware create/update/read schemas, migration_
_`b2c3d4e5f6a7` (upgrade+downgrade verified across all 3 revisions) — 160 tests, 100% cov._
_Frontend: EventForm type picker, EventsView type badge column — 127 vitest tests, 100%_
_lines, prod tsc clean. Code: `models/event.py`, `schemas/event.py`, `services/event_service.py`,_
_`migrations/versions/b2c3d4e5f6a7_*`, `components/EventForm.tsx`, `components/EventsView.tsx`,_
_`lib/events.ts`. Tests: `test_events.py`, `EventForm.test.tsx`, `EventsView.test.tsx`._
_Design rule recorded: types are composable modules; never fork the Event model per type._

_R7.2 VERIFIED: backend `SessionMode` enum + stream/meeting/recording URLs on Session,_
_session schema + service carry them, `list_recordings` + GET `/events/{id}/recordings`_
_(attendee-facing), migration `c3d4e5f6a7b8` (upgrade+downgrade verified), seed enriched_
_with online/hybrid sessions + recordings — 169 tests, 100% cov. Frontend: agenda mode_
_chips + live-stream/▶recording links + on-demand Recordings catalog — 132 tests, 100%_
_lines, prod tsc clean. Delivers the live-program / webinar-video / record-that feature._


## Sprint 2 — Auth, multi-tenancy, RBAC, Postgres, SSO, demo data

### Module 2A — Backend auth + tenancy ✅ VERIFIED (95 tests, 100% cov, exit 0)
| ID | Requirement | Code | Test | Status |
|----|-------------|------|------|--------|
| R2.1 | Tenant + User models, 3 roles | `models/identity.py` | `test_auth.py`, `test_deps.py` | ✅ |
| R2.2 | Password hashing + JWT | `core/security.py` | `test_google_sso.py` | ✅ |
| R2.3 | Email/password login | `api/auth.py`, `services/auth_service.py` | `test_auth.py`, `test_auth_service.py` | ✅ |
| R2.4 | Google SSO (optional, injectable verify) | `auth_service.py`, `core/deps.py` | `test_google_sso.py`, `test_deps.py` | ✅ |
| R2.5 | current-user dep + bearer | `core/deps.py` | `test_auth.py`, `test_deps.py` | ✅ |
| R2.6 | Super-admin spans all tenants | `api/events.py`, `event_service.py` | `test_events.py` | ✅ |
| R2.7 | Tenant-admin scoped to own tenant | `event_service.py`, `auth_service.py` | `test_events.py`, `test_auth.py` | ✅ |
| R2.8 | User role cannot write events | `api/events.py` | `test_events.py`, `test_api_helpers.py` | ✅ |
| R2.9 | Tenant isolation (no cross-tenant read) | `event_service.py` | `test_events.py` | ✅ |
| R2.10 | User management (scoped create/list) | `auth_service.py`, `api/auth.py` | `test_auth.py`, `test_auth_service.py` | ✅ |
| R2.11 | Tenant-admin can't mint super-admin (neg) | `auth_service.py` | `test_auth.py`, `test_auth_service.py` | ✅ |
| R2.12 | Conflict/401/403 handlers | `api/errors.py` | `test_auth.py`, `test_events.py` | ✅ |
| R2.13 | Demo seeder (idempotent) | `services/seed.py` | `test_seed.py` | ✅ |
| R2.14 | DB-aware readiness `/api/ready` | `api/health.py` | `test_health.py` | ✅ |
| R2.15 | Postgres persistence (prod) + Alembic migrations | `db/session.py`, `migrations/`, `docker-compose.yml`, `deploy/entrypoint.sh` | `alembic upgrade/downgrade` local + **Vultr deploy smoke ✅** (`/api/ready` = db ok, 2 tenants, 5 users; both containers healthy on `45.77.52.54:8095`) | ✅ |

_Verified via subprocess pytest: 95 passed, 100% coverage, exit 0. Pushed in this cycle._
_Bcrypt note: uses the `bcrypt` library directly (passlib 1.7.4 is incompatible with_
_bcrypt 5.x); long secrets are SHA-256 pre-hashed so no password is ever rejected._

### Module 2B — Frontend login + role-aware UI  ✅ VERIFIED (84 tests pass, exit 0)
| R2.16 | Login screen (password + Google, demo creds shown) | `components/LoginView.tsx`, `lib/auth.ts` | `LoginView.test.tsx`, `auth.test.ts`, `e2e/auth.spec.ts` | ✅ |
| R2.17 | Auth context + token storage (localStorage) | `lib/AuthContext.tsx`, `lib/authedFetch.ts` | `AuthContext.test.tsx`, `authedFetch.test.ts` | ✅ |
| R2.18 | Role-aware nav (admin Users tab; attendee read-only) | `App.tsx`, `components/EventsView.tsx` | `App.test.tsx`, `e2e/auth.spec.ts` | ✅ |
| R2.19 | User management UI (list + create, scoped roles) | `components/UsersView.tsx` | `UsersView.test.tsx` | ✅ |

_2B uses KendoReact Inputs/Buttons/Grid/Layout (role picker uses a native select for_
_testability + a11y). Verified: 84 vitest tests pass, statements/lines 100%; branch/func_
_floors documented in vite.config (v8 counts un-drivable Kendo portal handlers). axios_
_added as a Grid v11 peer dep; Grids wrapped in testid divs with `scrollable="none"` and_
_use the v11 `cells={{ data }}` custom-cell API._
_Auth token carried via `makeAuthedFetch` wrapper so the S1 events client stays unchanged._

**Demo credentials (seeded):** super@atelier.demo · admin@react-summit.demo ·
admin@vue-conf.demo · user@react-summit.demo — all password `Atelier!2026`.

_Secrets (Google client id/secret, JWT secret) supplied via env/.env or `gh secret`,_
_never committed. App runs fully in demo mode with zero keys (Google button hidden)._
