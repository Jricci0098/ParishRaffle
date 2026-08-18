# ---------- Stage 1: build the React frontend ----------
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ---------- Stage 2: Python backend serving the built frontend ----------
FROM python:3.11-slim AS app
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    STATIC_DIR=/app/static \
    DATABASE_URL=sqlite:////data/raffle.db \
    DEMO_DATABASE_URL=sqlite:////data/raffle-demo.db \
    BACKUP_DIR=/data/backups

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY --from=frontend /frontend/dist ./static

# Persistent data (SQLite database + backups).
RUN mkdir -p /data/backups
VOLUME ["/data"]

EXPOSE 8000

# A single worker is used so the in-process ticket-assignment lock guarantees
# no overlapping ticket numbers (see backend/app/services/sales.py).
# Shell form so ${PORT} (injected by Cloud Run and similar platforms) is honored;
# falls back to 8000 for local/Docker Compose use.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
