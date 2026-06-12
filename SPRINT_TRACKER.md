# Sprint Tracker — Convergence Atelier

**Rule (non-negotiable):** every mini-sprint ends GREEN and is independently
submittable. The loop, in this exact order:

```
build → git commit → push → test
   └─ on test error: git commit → push → test → repeat SAME error until fixed
   └─ never re-fix an error that already passed; move to next failure, then next sprint
```

Coverage gate to mark a sprint DONE:
- Unit (Vitest / pytest): 100% of sprint's defined units
- Functional (Playwright): 100% of sprint's defined flows
- Negative (Playwright): 100% of sprint's defined failure paths
- E2E (Playwright): 100% of sprint's defined journeys

Status legend: ⬜ not started · 🟨 in progress · ✅ done (green + pushed)

---

## S0 — Scaffold & rails  ✅
Goal: empty-but-runnable monorepo that builds, lints, tests, dockerizes, and deploys.
- [x] Monorepo layout (frontend / backend / e2e / deploy / docs)
- [x] FastAPI skeleton + `/api/health` + tz-aware declarative base
- [x] KendoReact + Vite + TS app shell + `/` health route
- [x] PWA manifest + service worker shell
- [x] Vitest + pytest + Playwright harnesses wired (each with passing smoke test)
- [x] Dockerfile (multi-stage) + docker-compose + `docker-compose.override.example.yml` (8095, `!override`)
- [x] GitHub Actions CI (lint → unit → build → e2e)
- [x] DEPLOY.md Vultr runbook
- [x] Remote repo created + first push green (https://github.com/vsenthil7/ConvergenceAtelier)
**Verified:** backend 8/8 100% · frontend 7/7 100% · e2e 8/8 (desktop+mobile) · build OK · pushed `c214b2c`.

## S1 — Events & agenda CRUD  ✅
Backend ✅ done · Frontend ✅ done.
- [x] Event + Session models (tz-aware) + validated CRUD API
- [x] Read/write schema split, UTC coercion for SQLite reads, central 404 handler
- [x] Backend unit + functional + negative 100% (**33 tests, 100% cov, pushed `d86a379`**)
- [x] Events Grid + Form UI (KendoReact)
- [x] Agenda/session scheduling via Scheduler
- [x] Frontend unit (Vitest) + functional + negative + E2E (Playwright) — **84 tests pass, exit 0**
**Verified:** frontend 84/84 (vitest), statements/lines 100%; e2e specs login-gated.

## S2 — Auth, multi-tenancy, RBAC, SSO, demo data  ✅
Module 2A backend ✅ · Module 2B frontend ✅ · Postgres (R2.15) ✅ (deployed + smoke-verified on Vultr).
- [x] 3-role model (super_admin → tenant_admin → user), Tenant + User models
- [x] Email/password (JWT) + optional Google SSO; demo mode hides Google when unset
- [x] RBAC + tenant isolation on events; scoped user management
- [x] Demo seeder (2 tenants, 5 users), DB-aware `/api/ready`
- [x] Backend **95 tests, 100% cov, `e978fbc`**
- [x] Frontend login + AuthContext + role-aware nav + Users UI (**84 tests, exit 0**)
- [x] Postgres persistence: compose on 5434 + Alembic migrations · **Vultr deploy smoke ✅** (`/api/ready` db ok)

## S2b — Speakers, sessions, sponsors, multi-track  ⬜
- [ ] Speaker/session/sponsor models + CRUD
- [ ] Multi-track timeline (Gantt) + conflict detection
- [ ] Unit + functional + negative + E2E 100%

## S3 — AI discovery & matchmaking  🟨
Module 3A backend ✅ (132 tests) · Module 3B frontend ✅ (105 tests): discovery UI + AI agenda-draft UI + one-tap demo login.
- [x] Semantic talk recommendations (deterministic keyless embeddings in demo mode)
- [x] Attendee↔speaker / attendee↔attendee matchmaking (backend service + API)
- [x] AI agenda draft (theme → ordered, track-grouped running order) — backend + frontend UI
- [x] One-tap demo sign-in (no typing; shared password never displayed)
- [x] Backend unit + functional + negative 100% (**132 tests, 100% cov, exit 0**)
- [x] Frontend discovery + agenda-draft UI 100% lines (**105 tests, exit 0**)
- [ ] Matchmaking frontend view (attendee↔attendee) + Discovery E2E (Playwright)

## S3b — Event registration & participation  ✅  (closes real product gaps)
Backend ✅ (156 tests, 100% cov, `41c5ade`) · Frontend ✅ (125 tests, exit 0, 100% lines).
- [x] **Public self-registration**: `POST /api/auth/register` (creates a `user` in a
      chosen public tenant; rejects privileged-role self-grant) — backend + Login panel ✅
- [x] **Event registration model**: `EventRegistration(event_id, user_id, status)` +
      register / cancel / my-status / participants endpoints (attendee self-serves; admin roster) ✅
- [x] **Event page participation (frontend)**: Register / Registered ✓ toggle for attendees; roster for admins ✅
- [x] **Seed real sessions** — 6 multi-track talks per demo event, scheduled ON the event day (fixes blank agenda) ✅
- [x] **Fix: Add-user button** — inline validation hints explain the disabled state ✅
- [x] **Fix: empty-agenda affordance** — "No sessions yet" message instead of a blank calendar ✅
- [x] Backend 156 tests / 100% cov · Frontend 125 tests / 100% lines · prod tsc clean

## S4 — Real-time engagement  ⬜
- [ ] Live Q&A, polls, session sentiment (websocket/SSE)
- [ ] Live attendance heatmap (streaming Charts)
- [ ] Unit + functional + negative + E2E 100%

## S5 — Attendee PWA & mobile  ⬜
- [ ] Personalised schedule + networking suggestions
- [ ] Installable mobile experience, offline shell, responsive
- [ ] Unit + functional + negative + E2E 100% (incl. mobile viewport)

## S6 — Analytics & deploy hardening  ⬜
- [ ] Engagement / attendance / sponsor-ROI dashboard (Charts, PivotGrid, TileLayout)
- [ ] Demo seed dataset
- [ ] Vultr deploy verified live + smoke
- [ ] Unit + functional + negative + E2E 100%

## S7 — Event TYPES: one platform, many event shapes  🟨  ← NEW (product vision)

**The big idea.** Today every event is the same shape (name/location/dates/sessions).
Real events are NOT interchangeable: a hackathon needs team formation + project
submissions + judging; a webinar needs a stream URL + registration cap + a recording;
an in-person conference needs rooms, tracks, and check-in. Convergence Atelier becomes
a *configurable* platform: pick an **event type** and the event unlocks the right
feature modules. This is the differentiator — one organiser tool that adapts to the
event instead of forcing every event into a calendar.

**Model:** add `Event.event_type` (enum) + a typed `Event.config` (JSON) so each type
carries its own settings without schema churn. Feature modules attach by type. The
existing agenda/sessions/registration layers are shared by all types (composition,
not duplication).

### Event types (MVP set) and their distinctive feature modules
| Type | What's distinctive | Module(s) to build |
|------|--------------------|--------------------|
| **conference** (default, exists) | multi-track agenda, speakers, rooms | agenda (have), tracks/rooms, check-in |
| **hackathon** | teams, project submissions, judging, leaderboard | Team model, Submission model + repo/demo links, Judging rubric + scores, live Leaderboard |
| **webinar** | single stream, capacity cap, recording, reminders | Stream URL + provider, registration cap + waitlist, recording link, reminder schedule |
| **meetup** | RSVP, venue, casual, recurring | RSVP cap, recurrence rule, venue map |
| **workshop** | limited seats, materials, prerequisites, cohort | Seat cap, materials/resource list, prerequisite gating |
| **hybrid / online-linked** | links physical + multiple online events, shared catalog | Event-to-event linking, cross-event session catalog, online/offline session mode |

### Cross-type capabilities (innovative, AI-first — reuse S3 discovery)
- **Session mode** per session: `in_person | online | hybrid`, with stream/recording URL + meeting link (webinar/program video feature requested by operator).
- **Recordings library**: any session can carry a recording URL → on-demand catalog after the event.
- **Linked events**: an online event can be "linked" to a physical one (same series); discovery + agenda-draft can span linked events.
- **Type-aware AI**: agenda-draft already exists; extend so a hackathon drafts a *judging schedule*, a webinar drafts a *promo timeline*, etc. (reuses the embedding engine — no new keys).

### Sprint breakdown (each lands GREEN independently, git-first, 100% cov)
- [x] **S7.1 Event type + config**: `event_type` enum + JSON `config` on Event; type-aware create/edit; migration; type badge on Events grid. Backend ✅ (160 tests, 100% cov) + frontend ✅ (127 tests, 100% lines, prod tsc clean).
- [x] **S7.2 Session mode + recordings** ✅: per-session `mode` (in_person/online/hybrid) + `stream_url`/`meeting_url`/`recording_url`; type-aware session schema/API; agenda shows mode chips + live-stream + ▶ recording links; "Recordings" on-demand catalog panel. Backend ✅ (169 tests, 100% cov, migration verified) + frontend ✅ (132 tests, 100% lines, prod tsc clean). Delivers the live-program / webinar-video / record-that capability.
  - R7.2.1 Session model: `mode` enum + `stream_url`/`recording_url`/`meeting_url` columns + migration ✅
  - R7.2.2 Session create/read schema carries mode + URLs (validated, optional) ✅
  - R7.2.3 Recordings query: list sessions across an event that have a recording_url ✅
  - R7.2.4 Frontend session client types + a recordings client call ✅
  - R7.2.5 Agenda shows a mode chip (online/in-person/hybrid) + ▶ recording link per talk ✅
  - R7.2.6 "Recordings" catalog panel on the event page (on-demand library) ✅
- [x] **S7.3 Hackathon module** ✅: the hackathon feature set that hangs off `event_type=hackathon`. Teams, project submissions with repo/demo links + tracking states, judging rubric + scores, and a live leaderboard — all composable over the shared event/registration core. Backend ✅ (198 tests, 100% cov, migration verified) + frontend ✅ (153 tests, 100% lines, prod tsc clean).
  - R7.3.1 `Team` model (event-scoped, name, members via membership) + migration ✅
  - R7.3.2 `Submission` model (team-scoped: title, summary, repo_url, demo_url, status enum draft/submitted/disqualified) + migration ✅
  - R7.3.3 `Score` model (submission × judge × criterion → value) for the judging rubric + migration ✅
  - R7.3.4 HackathonService: create/list teams, join team, create/submit submission, record scores, compute leaderboard (sum/avg per submission, ranked) ✅
  - R7.3.5 REST API under `/api/events/{id}/hackathon/*` (teams, submissions, scores, leaderboard) with RBAC (attendee joins/submits; admin/judge scores; leaderboard readable by all in-scope) ✅
  - R7.3.6 Frontend hackathon client (teams/submissions/scores/leaderboard types + calls) ✅
  - R7.3.7 Hackathon panel on the event page (only when event_type=hackathon): team list + my submission form + submit action ✅
  - R7.3.8 Live leaderboard (Kendo Grid) ranking submissions by total score ✅
  - Seed: one demo hackathon event (React Summit Hack 2026) with 2 teams, 2 submissions, and judge scores ✅
- [🟨] **S7.4 Webinar module** (IN PROGRESS): the webinar feature set that hangs off `event_type=webinar`. A capacity cap with automatic waitlist + promotion (built on S3b registration), the live stream + recording URLs (reuses S7.2 session media), and a reminder schedule — driven by the event `config`. Backend + frontend 100%.
  - R7.4.1 Extend `EventRegistration` with a `WAITLISTED` status + migration (capacity overflow goes to waitlist)
  - R7.4.2 WebinarService: capacity-aware register (REGISTERED until cap, then WAITLISTED), cancel auto-promotes the head of the waitlist, capacity/seat-count helper reading `config.capacity`
  - R7.4.3 REST: webinar-aware register/cancel reuse the events endpoints; add `GET /events/{id}/webinar/status` (capacity, registered_count, waitlisted_count, my_state) + `GET …/webinar/waitlist` (admin)
  - R7.4.4 Reminder schedule: compute reminder offsets from `config.reminders` (e.g. ["24h","1h"]) → `GET …/webinar/reminders` returns absolute send times relative to event start
  - R7.4.5 Frontend webinar client (status/waitlist/reminders types + calls)
  - R7.4.6 Webinar panel on the event page (only when event_type=webinar): join/leave with live seat counter, waitlist position, stream link when live, reminder list
  - R7.4.7 Seed: one demo webinar event (capacity + reminders in config, a stream URL) with some registrations incl. a waitlisted attendee
- [ ] **S7.5 Linked / hybrid events**: event-to-event links + cross-event session catalog; discovery spans linked events. 100%.
- [ ] **S7.6 Type-aware AI drafts**: agenda-draft variants per type (judging schedule / promo timeline / workshop plan). 100%.

_Rationale recorded so future sprints stay disciplined: build types as composable modules
over the shared event/session/registration core; never fork the Event model per type._


---

## Known traps pre-mitigated (from prior project post-mortems)
1. **Timezone-aware datetimes everywhere** — all DB columns `TIMESTAMPTZ`, all Python
   `datetime.now(timezone.utc)`. SQLite drops tzinfo on read, so read schemas coerce
   back to UTC-aware. (Prior project lost ~1.5h to naive/aware subtraction.)
2. **Port collisions on shared VPS** — override uses `!override` + reserved 8095 (and
   5434 for Postgres later). Occupied on box: 8080–8094, 5432–5433, 6379, 6006,
   9000–9001, 7880–7882.
3. **`pip-audit --strict` build gate** — pin deps to non-vulnerable versions up front.
4. **Spaced project path breaks the agent's command runner** — tests are run by
   launching the venv python as a subprocess argument, not via a shell command line.

## Build/run notes for the operator
First local/CI run does install+test. Commands:

```
# backend  (already installed; just run tests)
cd backend && .venv\Scripts\python -m pytest          # 33 tests, 100% cover

# frontend  (re-run install when new Kendo components are added)
cd frontend && npm install
npx kendo-ui-license activate            # uses telerik-license.txt at repo root
npm run test                             # vitest unit (100% thresholds)
npm run build                            # vite production build

# e2e
cd e2e && npm install && npx playwright install
npm test                                 # playwright functional+negative+e2e
```
