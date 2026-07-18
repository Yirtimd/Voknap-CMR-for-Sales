#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")/.."

test_database_name="${TEST_DATABASE_NAME:-cmr_quality_gate_test}"
if [[ ! "$test_database_name" =~ ^[a-z_][a-z0-9_]{0,62}$ ]]; then
  echo "TEST_DATABASE_NAME must be a valid PostgreSQL identifier"
  exit 1
fi

if [[ ! -x .venv/bin/python ]]; then
  echo "Missing .venv. Create it and install requirements-dev.txt"
  exit 1
fi
if [[ ! -d frontend/node_modules ]]; then
  echo "Missing frontend/node_modules. Run: npm --prefix frontend install"
  exit 1
fi
managed_test_database="false"
cleanup() {
  if [[ "$managed_test_database" == "true" ]]; then
    docker compose exec -T postgres \
      dropdb -U cmr --if-exists --force "$test_database_name" >/dev/null
  fi
}
trap cleanup EXIT INT TERM

echo "[1/7] Ruff"
.venv/bin/ruff check app tests scripts alembic

echo "[2/7] Backend unit tests"
.venv/bin/pytest -q -m "not postgres"

if [[ -z "${TEST_DATABASE_URL:-}" ]]; then
  if ! docker info >/dev/null 2>&1; then
    echo "Docker is not running. Start Docker Desktop and retry."
    exit 1
  fi
  echo "Preparing isolated PostgreSQL database: $test_database_name"
  docker compose up -d --wait postgres
  docker compose exec -T postgres \
    dropdb -U cmr --if-exists --force "$test_database_name"
  docker compose exec -T postgres createdb -U cmr "$test_database_name"
  export TEST_DATABASE_URL="postgresql+psycopg://cmr:cmr@localhost:5432/$test_database_name"
  managed_test_database="true"
fi

echo "[3/7] PostgreSQL migrations and integration tests"
DATABASE_URL="$TEST_DATABASE_URL" .venv/bin/alembic upgrade head
TEST_DATABASE_URL="$TEST_DATABASE_URL" .venv/bin/pytest -q -m postgres

echo "[4/7] Frontend typecheck"
npm --prefix frontend run typecheck

echo "[5/7] Frontend unit tests"
npm --prefix frontend run test

echo "[6/7] Frontend production build"
npm --prefix frontend run build

echo "[7/7] Alembic schema check"
DATABASE_URL="$TEST_DATABASE_URL" .venv/bin/alembic check

echo "Quality gate passed"
