# syntax=docker/dockerfile:1.6
# Multi-stage: build the KendoReact PWA, then serve it + the FastAPI backend.

# ---- Stage 1: frontend build (Kendo license activated at build time) ----
FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
# Activate the Kendo trial license from the build secret / env, then build.
ARG TELERIK_LICENSE=""
ENV TELERIK_LICENSE=${TELERIK_LICENSE}
RUN npm run build

# ---- Stage 2: backend runtime ----
FROM python:3.12-slim AS runtime
RUN groupadd -r atelier && useradd -r -g atelier -u 1001 atelier \
    && apt-get update && apt-get install -y --no-install-recommends nginx \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/pyproject.toml backend/pyproject.toml
RUN pip install --no-cache-dir -e backend/
COPY backend/ backend/
# Static SPA served by nginx; nginx proxies /api to uvicorn on 8000.
COPY --from=frontend /app/frontend/dist /usr/share/nginx/html
COPY deploy/nginx.conf /etc/nginx/sites-available/default
COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && chown -R atelier:atelier /app
EXPOSE 80
ENV USE_MOCKS=true
CMD ["/entrypoint.sh"]
