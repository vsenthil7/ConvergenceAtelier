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
| R0.4 | PWA installable (manifest+SW) | `frontend/public/manifest.webmanifest`, `vite-plugin-pwa` | `e2e/tests/pwa.spec.ts` | ✅ |
| R0.5 | E2E harness loads app | `e2e/playwright.config.ts` | `e2e/tests/smoke.spec.ts` | ✅ |
| R0.6 | Container builds & runs | `Dockerfile`, `docker-compose.yml` | CI build job | ✅ |
| R0.7 | CI runs lint+unit+build+e2e | `.github/workflows/ci.yml` | CI green | ✅ |
| R0.8 | Vultr deploy documented | `DEPLOY.md` | manual smoke | ✅ |

## Sprint 1 — Events & agenda (placeholder, filled at S1)
| ID | Requirement | Code | Test | Status |
|----|-------------|------|------|--------|
| R1.1 | Create/read/update/delete event | tbd | tbd | ⬜ |
| R1.2 | Agenda sessions on Scheduler | tbd | tbd | ⬜ |

_S2–S6 rows appended as each sprint begins._
