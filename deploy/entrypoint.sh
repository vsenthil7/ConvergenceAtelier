#!/usr/bin/env bash
set -euo pipefail

cd /app/backend

# Apply Alembic migrations when pointed at a real database (Postgres in prod).
# In demo/SQLite mode the app creates tables on startup, so migrations are
# optional there; we still attempt them but never let a failure block boot.
if [[ "${DATABASE_URL:-}" == postgresql* ]]; then
  echo "[entrypoint] running Alembic migrations against Postgres..."
  if ! python -m alembic upgrade head; then
    echo "[entrypoint] WARNING: alembic upgrade failed; continuing (startup create_all will run)" >&2
  fi
fi

# Start the FastAPI backend (internal :8000), then nginx (public :80).
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
nginx -g "daemon off;"
