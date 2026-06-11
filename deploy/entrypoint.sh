#!/usr/bin/env bash
set -euo pipefail

# Start the FastAPI backend (internal :8000), then nginx (public :80).
cd /app/backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
nginx -g "daemon off;"
