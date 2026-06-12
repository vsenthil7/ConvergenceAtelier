# Traceability Matrix — Convergence Atelier

Requirement → Code → Test → Status. Updated every sprint. A requirement is DONE only
when its unit + functional + negative + E2E rows are all ✅ and pushed.

Status: ⬜ todo · 🟨 in progress · ✅ done

## Sprint 0 — Scaffold & rails

| ID | Requirement | Code | Test | Status |
|----|-------------|------|------|--------|
| R0.1 | Backend serves health check | `backend/app/main.py` `/api/health` | `backend/tests/test_health.py` | ✅ |
| R0.2 | Datetime base is tz-aware | `backend/app/db/base.py` | `backend/tests/test_tzaware.py` | ✅ |
| R0.3 | Frontend app shell renders + Kendo license | `frontend/src/App.tsx` | `frontend/src/__tests__/App.test.tsx` | ✅ |
| R0.4 | PWA installable (manifest+SW) | `frontend/vite.config.ts` | `e2e/tests/pwa.spec.ts` | ✅ |
| R0.5 | E2E harness loads app | `e2e/playwright.config.ts` | `e2e/tests/smoke.spec.ts` | ✅ |
| R0.6 | Container builds & runs | `Dockerfile`, `docker-compose.yml` | CI build job | ✅ |
| R0.7 | CI runs lint+unit+build+e2e | `.github/workflows/ci.yml` | CI green | ✅ |
| R0.8 | Vultr deploy documented | `DEPLOY.md` | manual smoke | ✅ |

**S0 verified:** backend 8/8 100% cov · frontend 7/7 100% cov · e2e 8/8 (desktop+mobile) · build OK.

## Sprint 1 — Events & agenda CRUD

| ID | Requirement | Code | Test | Status |
|----|-------------|------|------|--------|
| R1.1 | Event model is tz-aware | `backend/app/models/event.py` | `tests/test_event_service.py` | ✅ |
| R1.2 | Create event (validated) | `app/api/events.py` POST | `tests/test_events.py::test_create_and_get_event` | ✅ |
| R1.3 | List events | `app/api/events.py` GET | `tests/test_events.py::test_list_*` | ✅ |
| R1.4 | Get event by id | `app/api/events.py` GET id | `tests/test_events.py::test_create_and_get_event` | ✅ |
| R1.5 | Update event (partial) | `app/api/events.py` PATCH | `tests/test_events.py::test_update_event` | ✅ |
| R1.6 | Delete event | `app/api/events.py` DELETE | `tests/test_events.py::test_delete_event` | ✅ |
| R1.7 | Add agenda session | `app/api/events.py` POST sessions | `tests/test_events.py::test_add_session_to_event` | ✅ |
| R1.8 | Reject end<=start (neg) | `app/schemas/event.py` validator | `tests/test_events.py::*end_before_start*` | ✅ |
| R1.9 | Reject naive datetimes (neg) | `app/schemas/event.py` validator | `tests/test_events.py::*naive*` | ✅ |
| R1.10 | 404 on missing entity (neg) | `app/api/errors.py` handler | `tests/test_events.py::*missing*` | ✅ |
| R1.11 | Events Grid + Form UI | `frontend` (next) | `frontend` vitest + e2e | ⬜ |
| R1.12 | Agenda on Scheduler | `frontend` (next) | `frontend` vitest + e2e | ⬜ |

**S1 backend verified (ran locally):** 33 tests pass, 100% coverage, exit 0, pushed `d86a379`.
Frontend (R1.11–R1.12) is the remaining S1 work.

_S2–S6 rows appended as each sprint begins._
