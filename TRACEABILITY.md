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
| R2.15 | Postgres persistence (prod) | `db/session.py`, compose | deploy smoke | ⬜ |

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
