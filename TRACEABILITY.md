# Traceability Matrix — Convergence Atelier

Requirement → Code → Test → Status. Status: ⬜ todo · 🟨 in progress · ✅ done.
A requirement is DONE only when its tests pass at 100% coverage and are pushed.

## Sprint 0 — Scaffold & rails  ✅
backend 8/8 · frontend 7/7 · e2e 8/8 · build OK · `c214b2c`.

## Sprint 1 — Events & agenda CRUD
- Backend ✅ (33 tests, 100%, `d86a379`)
- Frontend 🟨 authored (Grid/Form/Scheduler + tests), awaiting `npm install` verify (`287d7d6`)

## Sprint 2 — Auth, multi-tenancy, RBAC, Postgres, SSO, demo data

### Module 2A — Backend auth + tenancy (authored, awaiting verify)
| ID | Requirement | Code | Test | Status |
|----|-------------|------|------|--------|
| R2.1 | Tenant + User models, 3 roles | `models/identity.py` | `test_auth.py`, `test_deps.py` | 🟨 |
| R2.2 | Password hashing + JWT | `core/security.py` | `test_google_sso.py` | 🟨 |
| R2.3 | Email/password login | `api/auth.py`, `services/auth_service.py` | `test_auth.py` | 🟨 |
| R2.4 | Google SSO (optional, injectable verify) | `auth_service.py`, `core/deps.py` | `test_google_sso.py`, `test_deps.py` | 🟨 |
| R2.5 | current-user dep + bearer | `core/deps.py` | `test_auth.py`, `test_deps.py` | 🟨 |
| R2.6 | Super-admin spans all tenants | `api/events.py`, `event_service.py` | `test_events.py` | 🟨 |
| R2.7 | Tenant-admin scoped to own tenant | `event_service.py`, `auth_service.py` | `test_events.py`, `test_auth.py` | 🟨 |
| R2.8 | User role cannot write events | `api/events.py` | `test_events.py` | 🟨 |
| R2.9 | Tenant isolation (no cross-tenant read) | `event_service.py` | `test_events.py` | 🟨 |
| R2.10 | User management (scoped create/list) | `auth_service.py`, `api/auth.py` | `test_auth.py` | 🟨 |
| R2.11 | Tenant-admin can't mint super-admin (neg) | `auth_service.py` | `test_auth.py` | 🟨 |
| R2.12 | Conflict/401/403 handlers | `api/errors.py` | `test_auth.py`, `test_events.py` | 🟨 |
| R2.13 | Demo seeder (idempotent) | `services/seed.py` | `test_seed.py` | 🟨 |
| R2.14 | DB-aware readiness `/api/ready` | `api/health.py` | `test_health.py` | 🟨 |
| R2.15 | Postgres persistence (prod) | `db/session.py`, compose | deploy smoke | ⬜ |

### Module 2B — Frontend login + role-aware UI  ⬜
| R2.16 | Login screen (password + Google) | `frontend` (next) | vitest + e2e | ⬜ |
| R2.17 | Auth context + token storage | `frontend` (next) | vitest | ⬜ |
| R2.18 | Role-aware nav (admin/user views) | `frontend` (next) | vitest + e2e | ⬜ |
| R2.19 | User management UI (admins) | `frontend` (next) | vitest + e2e | ⬜ |

**Demo credentials (seeded):** super@atelier.demo · admin@react-summit.demo ·
admin@vue-conf.demo · user@react-summit.demo — all password `Atelier!2026`.

_Secrets (Google client id/secret, JWT secret) supplied via env/.env or `gh secret`,_
_never committed. App runs fully in demo mode with zero keys (Google button hidden)._
