# Deploy — Convergence Atelier on Vultr

Single-container app (nginx serves the KendoReact PWA, proxies `/api` to FastAPI).
Reserved host port **8095** — clear of every other project on the box.

## Occupied ports on the VPS (do not reuse)
8080–8094, 5432–5433, 6379, 6006, 9000–9001, 7880–7882.
Convergence Atelier uses **8095** (and reserves **5434** for Postgres in a later sprint).

## First deploy

```bash
ssh root@45.77.52.54
cd /srv
rm -rf convergence
git clone https://github.com/vsenthil7/ConvergenceAtelier.git convergence
cd convergence

# Kendo license for the frontend build (paste your trial key, or scp the file):
export TELERIK_LICENSE="$(cat /root/telerik-license.txt)"

# Remap port 80 -> 8095 (override is gitignored; copy from the example):
cp docker-compose.override.example.yml docker-compose.override.yml

docker compose up -d --build
```

## Verify

```bash
curl -s -o /dev/null -w "app: %{http_code}\n"    http://localhost:8095/
curl -s http://localhost:8095/api/health; echo
docker compose ps
```

Expected: app `200`, health JSON `{"status":"ok",...}`.

Public URL once up: `http://45.77.52.54:8095/`

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
