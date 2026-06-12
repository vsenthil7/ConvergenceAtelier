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

**S0 verified:** backend 8/8 100% · frontend 7/7 100% · e2e 8/8 (desktop+mobile) · build OK · `c214b2c`.

## Sprint 1 — Events & agenda CRUD

### Backend (verified locally — 33 tests, 100% cov, `d86a379`)
| ID | Requirement | Code | Test | Status |
|----|-------------|------|------|--------|
| R1.1 | Event model is tz-aware | `backend/app/models/event.py` | `tests/test_event_service.py` | ✅ |
| R1.2 | Create event (validated) | `app/api/events.py` POST | `tests/test_events.py` | ✅ |
| R1.3 | List events | `app/api/events.py` GET | `tests/test_events.py` | ✅ |
| R1.4 | Get event by id | `app/api/events.py` GET id | `tests/test_events.py` | ✅ |
| R1.5 | Update event (partial) | `app/api/events.py` PATCH | `tests/test_events.py` | ✅ |
| R1.6 | Delete event | `app/api/events.py` DELETE | `tests/test_events.py` | ✅ |
| R1.7 | Add agenda session | `app/api/events.py` POST sessions | `tests/test_events.py` | ✅ |
| R1.8 | Reject end<=start (neg) | `app/schemas/event.py` | `tests/test_events.py` | ✅ |
| R1.9 | Reject naive datetimes (neg) | `app/schemas/event.py` | `tests/test_events.py` | ✅ |
| R1.10 | 404 on missing entity (neg) | `app/api/errors.py` | `tests/test_events.py` | ✅ |

### Frontend (authored — awaiting one `npm install` then verify)
| ID | Requirement | Code | Test | Status |
|----|-------------|------|------|--------|
| R1.11 | Typed events API client | `frontend/src/lib/events.ts` | `__tests__/events.test.ts` | 🟨 |
| R1.12 | Client validation mirrors API | `frontend/src/lib/validation.ts` | `__tests__/validation.test.ts` | 🟨 |
| R1.13 | Event Form (Kendo inputs) | `frontend/src/components/EventForm.tsx` | `__tests__/EventForm.test.tsx` | 🟨 |
| R1.14 | Events Grid + create/delete + Scheduler agenda | `frontend/src/components/EventsView.tsx` | `__tests__/EventsView.test.tsx` | 🟨 |
| R1.15 | Events flow E2E (functional+negative) | `frontend` | `e2e/tests/events.spec.ts` | 🟨 |

_Frontend uses KendoReact Grid, Form/Inputs, DateTimePicker, Dialog, Scheduler. New_
_packages require one `npm install` in frontend/ before the suite runs._

_S2–S6 rows appended as each sprint begins._
