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

## S2 — Auth, multi-tenancy, RBAC, SSO, demo data  🟨
Module 2A backend ✅ · Module 2B frontend ✅ · Postgres (R2.15) ⬜ remaining.
- [x] 3-role model (super_admin → tenant_admin → user), Tenant + User models
- [x] Email/password (JWT) + optional Google SSO; demo mode hides Google when unset
- [x] RBAC + tenant isolation on events; scoped user management
- [x] Demo seeder (2 tenants, 5 users), DB-aware `/api/ready`
- [x] Backend **95 tests, 100% cov, `e978fbc`**
- [x] Frontend login + AuthContext + role-aware nav + Users UI (**84 tests, exit 0**)
- [~] Postgres persistence: compose on 5434 + Alembic migrations ✅ (upgrade/downgrade verified) · Vultr deploy smoke ⬜

## S2b — Speakers, sessions, sponsors, multi-track  ⬜
- [ ] Speaker/session/sponsor models + CRUD
- [ ] Multi-track timeline (Gantt) + conflict detection
- [ ] Unit + functional + negative + E2E 100%

## S3 — AI discovery & matchmaking  🟨
Module 3A backend ✅ (126 tests, 100% cov) · Frontend discovery UI ⬜ · AI agenda draft ⬜.
- [x] Semantic talk recommendations (deterministic keyless embeddings in demo mode)
- [x] Attendee↔speaker / attendee↔attendee matchmaking (backend service + API)
- [x] Backend unit + functional + negative 100% (**126 tests, 100% cov, exit 0**)
- [ ] AI agenda draft (AI Prompt + AI Chat)
- [ ] Frontend discovery UI (recommendations + matchmaking views) + E2E

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
