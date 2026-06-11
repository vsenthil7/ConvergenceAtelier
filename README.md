# Convergence Atelier

> The all-in-one organiser platform for modern tech conferences — where attendees,
> speakers, content, and live interaction converge in one studio.

Built for the **Progress x GitNation Hackathon** (JSNation / React Summit, Jun 2026).

## Required stack (the hackathon "must")

This project is built on **KendoReact** (Progress Kendo UI for React) — the mandatory
component library for the challenge. Premium components used: Grid, Form, Scheduler,
Gantt, Charts, PivotGrid, AI Prompt, AI Chat, TileLayout, Drawer, Notification.

AI-in-the-build uses the **KendoReact MCP Server** (`@progress/kendo-react-mcp`) and its
Agentic UI Generator for component-accurate code generation.

## What it does (full organiser-platform scope)

| Area | Capability | Key Kendo components |
|------|-----------|----------------------|
| Organiser cockpit | Event/agenda/speaker/sponsor CRUD, multi-track scheduling | Grid, Form, Scheduler, Gantt |
| AI discovery | Semantic talk recommendations, attendee↔speaker matchmaking, AI agenda draft | AI Prompt, AI Chat |
| Live engagement | Q&A, polls, session sentiment, attendance heatmap | Charts (streaming), Notification |
| Attendee app (PWA) | Personalised schedule, networking, mobile install | Drawer, Scheduler, ListView |
| Analytics | Engagement, attendance, sponsor ROI | Charts, PivotGrid, TileLayout |

## Architecture

- **Frontend:** React 18 + TypeScript + Vite, KendoReact, PWA (installable, offline shell)
- **Backend:** FastAPI (async) + PostgreSQL, all datetimes timezone-aware (UTC)
- **Demo mode:** `USE_MOCKS=true` serves deterministic seed data — no external keys needed
- **Tests:** Vitest (unit), Playwright (E2E + functional + negative) — 100% of defined flows
- **Deploy:** Docker → GitHub → Vultr VPS pull-and-run (ports 8095 web / 8096 api / 5434 db)

## Local development

```bash
# backend
cd backend && python -m venv .venv && .venv\Scripts\activate
pip install -e .[dev]
uvicorn app.main:app --reload --port 8096

# frontend
cd frontend && npm install && npm run dev
```

## Project governance

- `SPRINT_TRACKER.md` — mini-sprint status, every sprint independently submittable
- `TRACEABILITY.md` — requirement → code → test → coverage status
- `DEPLOY.md` — Vultr deployment runbook

## Engineering loop (per sprint)

`build → git commit → push → test → (on error: git commit → push → test → repeat
until fixed) → next`. Git commit always precedes test. Coverage bar per sprint:
unit 100%, functional 100%, negative 100%, Playwright E2E 100% of defined flows.
