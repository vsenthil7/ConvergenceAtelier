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

## S0 — Scaffold & rails  🟨
Goal: empty-but-runnable monorepo that builds, lints, tests, dockerizes, and deploys.
- [x] Monorepo layout (frontend / backend / e2e / deploy / docs)
- [x] FastAPI skeleton + `/api/health` + tz-aware declarative base
- [x] KendoReact + Vite + TS app shell + `/` health route
- [x] PWA manifest + service worker shell
- [x] Vitest + pytest + Playwright harnesses wired (each with passing smoke test)
- [x] Dockerfile (multi-stage) + docker-compose + `docker-compose.override.yml` (8095/8096/5434, `!override`)
- [x] GitHub Actions CI (lint → unit → build → e2e)
- [x] DEPLOY.md Vultr runbook
- [ ] Remote repo created + first push green   ← in progress

## S1 — Events & agenda CRUD  ⬜
- [ ] Event model/CRUD API (tz-aware) + Grid + Form
- [ ] Agenda/session scheduling via Scheduler
- [ ] Unit + functional + negative + E2E 100%

## S2 — Speakers, sessions, sponsors, multi-track  ⬜
- [ ] Speaker/session/sponsor models + CRUD
- [ ] Multi-track timeline (Gantt) + conflict detection
- [ ] Unit + functional + negative + E2E 100%

## S3 — AI discovery & matchmaking  ⬜
- [ ] Semantic talk recommendations (mock embeddings in demo mode)
- [ ] Attendee↔speaker / attendee↔attendee matchmaking
- [ ] AI agenda draft (AI Prompt + AI Chat)
- [ ] Unit + functional + negative + E2E 100%

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
   `datetime.now(timezone.utc)`. (Prior project lost ~1.5h to naive/aware subtraction.)
2. **Port collisions on shared VPS** — override uses `!override` + reserved 8095/8096/5434.
   Occupied on box: 8080–8094, 5432–5433, 6379, 6006, 9000–9001, 7880–7882.
3. **`pip-audit --strict` build gate** — pin deps to non-vulnerable versions up front.

## Build/run notes for the operator
Because this codebase was authored by an agent whose runner could not execute installs
reliably, the **first** local/CI run does install+test. Commands:

```
# backend
cd backend && python -m venv .venv && .venv\Scripts\python -m pip install -e .[dev]
.venv\Scripts\python -m pytest          # expect 100% pass, 100% cover

# frontend
cd frontend && npm install
npx kendo-ui-license activate            # uses telerik-license.txt at repo root
npm run test                             # vitest unit
npm run build                            # vite production build

# e2e
cd e2e && npm install && npx playwright install --with-deps
npm test                                 # playwright functional+negative+e2e
```
