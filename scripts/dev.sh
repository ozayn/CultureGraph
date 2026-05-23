#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

export DATABASE_URL="${DATABASE_URL:-postgresql://culturegraph:culturegraph@localhost:5432/culturegraph}"
export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:8000}"

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

if [ ! -d backend/.venv ]; then
  python3 -m venv backend/.venv
fi

# shellcheck disable=SC1091
source backend/.venv/bin/activate
pip install -q -r backend/requirements.txt

cd backend
alembic upgrade head
PYTHONPATH=. python scripts/seed.py
cd "$ROOT_DIR"

if [ ! -d frontend/node_modules ]; then
  (cd frontend && npm install)
fi

cleanup() {
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT

(
  cd backend
  uvicorn app.main:app --reload --host "${API_HOST:-0.0.0.0}" --port "${API_PORT:-8000}"
) &
BACKEND_PID=$!

(
  cd frontend
  npm run dev
) &
FRONTEND_PID=$!

echo "CultureGraph running:"
echo "  Frontend: http://localhost:3000"
echo "  Backend:  ${NEXT_PUBLIC_API_URL}"

wait
