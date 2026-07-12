#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")/.."

if [[ ! -x .venv/bin/python ]]; then
  echo "Missing .venv. Create it and install requirements-dev.txt"
  exit 1
fi

if [[ ! -d frontend/node_modules ]]; then
  echo "Missing frontend/node_modules. Run: cd frontend && npm install"
  exit 1
fi

if [[ ! -f .env ]]; then
  echo "Note: .env not found; application defaults will be used"
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running. Start Docker Desktop and retry."
  exit 1
fi

echo "Starting PostgreSQL..."
docker compose up -d --wait postgres

echo "Applying migrations..."
.venv/bin/alembic upgrade head

backend_pid=""
cleanup() {
  if [[ -n "$backend_pid" ]] && kill -0 "$backend_pid" 2>/dev/null; then
    kill "$backend_pid" 2>/dev/null || true
    wait "$backend_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

echo "Backend: http://localhost:8000"
.venv/bin/uvicorn app.main:app --reload &
backend_pid=$!

echo "Frontend: http://localhost:5173"
npm --prefix frontend run dev
