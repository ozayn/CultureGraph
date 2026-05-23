#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Resolve app directories (apps/* symlinks or legacy backend/frontend).
if [ -d "$ROOT_DIR/apps/api" ]; then
  API_DIR="apps/api"
elif [ -d "$ROOT_DIR/backend" ]; then
  API_DIR="backend"
else
  echo "Error: API directory not found (expected apps/api or backend)."
  exit 1
fi

if [ -d "$ROOT_DIR/apps/web" ]; then
  WEB_DIR="apps/web"
elif [ -d "$ROOT_DIR/frontend" ]; then
  WEB_DIR="frontend"
else
  echo "Error: Web directory not found (expected apps/web or frontend)."
  exit 1
fi

load_env_file() {
  local file=$1
  if [ -f "$file" ]; then
    echo "  · $file"
    set -a
    # shellcheck disable=SC1090
    source "$file"
    set +a
  fi
}

echo "CultureGraph — loading environment"
load_env_file "$ROOT_DIR/.env"
load_env_file "$ROOT_DIR/$API_DIR/.env"
load_env_file "$ROOT_DIR/$WEB_DIR/.env.local"

# Local defaults (never bind to port 5000).
unset PORT
export API_HOST="${API_HOST:-0.0.0.0}"
export API_PORT="${API_PORT:-8000}"
export WEB_PORT="${WEB_PORT:-3000}"
export DATABASE_URL="${DATABASE_URL:-postgresql://culturegraph:culturegraph@localhost:5432/culturegraph}"
export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:8000}"
export CORS_ORIGINS="${CORS_ORIGINS:-http://localhost:3000}"

if [ "$API_PORT" = "5000" ] || [ "$WEB_PORT" = "5000" ]; then
  echo "Error: port 5000 is not used by CultureGraph. Set API_PORT=8000 and WEB_PORT=3000."
  exit 1
fi

echo ""
echo "CultureGraph — preparing dependencies"

if [ ! -d "$ROOT_DIR/$API_DIR/.venv" ]; then
  echo "  · Creating Python virtualenv"
  python3 -m venv "$ROOT_DIR/$API_DIR/.venv"
fi

# shellcheck disable=SC1091
source "$ROOT_DIR/$API_DIR/.venv/bin/activate"
pip install -q -r "$ROOT_DIR/$API_DIR/requirements.txt"

if [ ! -d "$ROOT_DIR/$WEB_DIR/node_modules" ]; then
  echo "  · Installing npm packages"
  (cd "$ROOT_DIR/$WEB_DIR" && npm install)
fi

echo "  · Running database migrations"
(cd "$ROOT_DIR/$API_DIR" && alembic upgrade head)

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo ""
  echo "CultureGraph — shutting down"
  if [ -n "$BACKEND_PID" ]; then
    kill "$BACKEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
  fi
  if [ -n "$FRONTEND_PID" ]; then
    kill "$FRONTEND_PID" 2>/dev/null || true
    wait "$FRONTEND_PID" 2>/dev/null || true
  fi
  echo "Done."
}

trap cleanup EXIT INT TERM

echo ""
echo "CultureGraph — starting services"
echo "  API   http://localhost:${API_PORT}"
echo "  Web   http://localhost:${WEB_PORT}"
echo ""
echo "Press Ctrl+C to stop both servers."
echo ""

(
  cd "$ROOT_DIR/$API_DIR"
  export PYTHONPATH=.
  uvicorn app.main:app --reload --host "$API_HOST" --port "$API_PORT"
) &
BACKEND_PID=$!

(
  cd "$ROOT_DIR/$WEB_DIR"
  npm run dev -- --port "$WEB_PORT"
) &
FRONTEND_PID=$!

wait "$BACKEND_PID" "$FRONTEND_PID"
