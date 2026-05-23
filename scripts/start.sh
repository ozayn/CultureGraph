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
