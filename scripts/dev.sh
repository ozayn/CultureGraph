#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# shellcheck disable=SC1091
source "$ROOT_DIR/scripts/lib/load-env.sh"

culturegraph_print_env_status
culturegraph_load_env

API_DIR="$CULTUREGRAPH_API_DIR"
WEB_DIR="$CULTUREGRAPH_WEB_DIR"

if command -v docker >/dev/null 2>&1; then
  docker compose up -d db
  echo "Waiting for PostgreSQL (Docker)..."
  until docker compose exec -T db pg_isready -U culturegraph >/dev/null 2>&1; do
    sleep 1
  done
elif command -v pg_isready >/dev/null 2>&1; then
  echo "Waiting for local PostgreSQL..."
  until pg_isready -h localhost >/dev/null 2>&1; do
    sleep 1
  done
else
  echo "PostgreSQL is required. Install Docker or a local Postgres server."
  exit 1
fi

if [ ! -d "$ROOT_DIR/$API_DIR/.venv" ]; then
  python3 -m venv "$ROOT_DIR/$API_DIR/.venv"
fi

# shellcheck disable=SC1091
source "$ROOT_DIR/$API_DIR/.venv/bin/activate"
pip install -q -r "$ROOT_DIR/$API_DIR/requirements.txt"

cd "$ROOT_DIR/$API_DIR"
alembic upgrade head
PYTHONPATH=. python scripts/seed.py
cd "$ROOT_DIR"

if [ ! -d "$ROOT_DIR/$WEB_DIR/node_modules" ]; then
  (cd "$ROOT_DIR/$WEB_DIR" && npm install)
fi

cleanup() {
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT

(
  cd "$ROOT_DIR/$API_DIR"
  uvicorn app.main:app --reload --host "$API_HOST" --port "$API_PORT"
) &
BACKEND_PID=$!

(
  cd "$ROOT_DIR/$WEB_DIR"
  npm run dev -- --port "$WEB_PORT"
) &
FRONTEND_PID=$!

echo "CultureGraph running:"
echo "  Web   http://localhost:${WEB_PORT}"
echo "  API   http://localhost:${API_PORT}"

wait
