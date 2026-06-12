# Deploy — Convergence Atelier on Vultr

Single-container app (nginx serves the KendoReact PWA, proxies `/api` to FastAPI).
Reserved host port **8095** — clear of every other project on the box.

## Occupied ports on the VPS (do not reuse)
8080–8094, 5432–5433, 6379, 6006, 9000–9001, 7880–7882.
Convergence Atelier uses **8095** (app) and **5434** (Postgres).

## First deploy

```bash
ssh root@45.77.52.54
cd /srv
rm -rf convergence
git clone https://github.com/vsenthil7/ConvergenceAtelier.git convergence
cd convergence

# Kendo license for the frontend build (build-time only). The file is gitignored,
# so it is NOT in the clone — upload it first from your machine:
#   scp telerik-license.txt root@45.77.52.54:/root/telerik-license.txt
# Then load it (the `2>/dev/null` keeps things quiet if it is missing — the build
# still works in Kendo trial mode without it):
export TELERIK_LICENSE="$(cat /root/telerik-license.txt 2>/dev/null || true)"

# Remap port 80 -> 8095 (override is gitignored; copy from the example):
cp docker-compose.override.example.yml docker-compose.override.yml

docker compose up -d --build
```

## Verify

```bash
curl -s -o /dev/null -w "app: %{http_code}\n"    http://localhost:8095/
curl -s http://localhost:8095/api/health; echo
curl -s http://localhost:8095/api/ready; echo   # DB-aware readiness
docker compose ps
```

Expected: app `200`, health JSON `{"status":"ok",...}`, ready JSON reporting the
database reachable. With the override above the app runs against Postgres on 5434
(`USE_MOCKS=false`); without it, the app falls back to the bundled SQLite demo.

Public URL once up: `http://45.77.52.54:8095/`

## Database & migrations
- Production persists to **Postgres** (the `db` service, host port 5434). The app
  reads `DATABASE_URL`; set it to `postgresql+asyncpg://atelier:atelier@db:5432/atelier`
  (the override does this). Change the credentials via `POSTGRES_USER/PASSWORD/DB`.
- **Alembic** migrations live in `backend/migrations/`. The container entrypoint
  runs `alembic upgrade head` automatically on boot whenever `DATABASE_URL` is
  Postgres, so a fresh box self-migrates.
- To run migrations manually inside the running container:
  ```bash
  docker compose exec app sh -c "cd /app/backend && python -m alembic upgrade head"
  ```
- To autogenerate a new migration after model changes (local dev):
  ```bash
  cd backend && python -m alembic revision --autogenerate -m "describe change"
  ```
- Demo mode (`USE_MOCKS=true`, no `DATABASE_URL`) uses SQLite and `create_all` on
  startup, so it needs no migration step to run.

## Update an existing deploy

```bash
cd /srv/convergence
git pull origin main
docker compose up -d --build
```

## Notes
- The Kendo license is supplied to the **build** via `TELERIK_LICENSE`. Keep
  `telerik-license.txt` out of git (already gitignored).
- `USE_MOCKS=true` is the default, so the demo needs no external API keys.
- Backend runs internally on :8000; only nginx (:80 → host 8095) is exposed.
