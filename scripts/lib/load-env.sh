#!/usr/bin/env bash
# Shared env loading for CultureGraph local scripts.
# Source from repo scripts; do not execute directly.

if [ -z "${ROOT_DIR:-}" ]; then
  echo "Error: ROOT_DIR must be set before sourcing load-env.sh" >&2
  return 1 2>/dev/null || exit 1
fi

if [ -d "$ROOT_DIR/apps/api" ]; then
  CULTUREGRAPH_API_DIR="apps/api"
elif [ -d "$ROOT_DIR/backend" ]; then
  CULTUREGRAPH_API_DIR="backend"
else
  echo "Error: API directory not found (expected apps/api or backend)." >&2
  return 1 2>/dev/null || exit 1
fi

if [ -d "$ROOT_DIR/apps/web" ]; then
  CULTUREGRAPH_WEB_DIR="apps/web"
elif [ -d "$ROOT_DIR/frontend" ]; then
  CULTUREGRAPH_WEB_DIR="frontend"
else
  echo "Error: Web directory not found (expected apps/web or frontend)." >&2
  return 1 2>/dev/null || exit 1
fi

CULTUREGRAPH_ROOT_ENV="$ROOT_DIR/.env"
CULTUREGRAPH_API_ENV="$ROOT_DIR/$CULTUREGRAPH_API_DIR/.env"
CULTUREGRAPH_WEB_ENV="$ROOT_DIR/$CULTUREGRAPH_WEB_DIR/.env.local"

culturegraph_report_env_file() {
  local label=$1
  local file=$2
  if [ -f "$file" ]; then
    echo "  found:   $label ($file)"
  else
    echo "  missing: $label ($file)"
  fi
}

culturegraph_load_env_file() {
  local file=$1
  if [ -f "$file" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$file"
    set +a
  fi
}

culturegraph_print_env_status() {
  echo "CultureGraph — environment files"
  culturegraph_report_env_file "root .env (optional)" "$CULTUREGRAPH_ROOT_ENV"
  culturegraph_report_env_file "API .env" "$CULTUREGRAPH_API_ENV"
  culturegraph_report_env_file "Web .env.local" "$CULTUREGRAPH_WEB_ENV"
  echo "  (values are not printed)"
}

culturegraph_load_env() {
  culturegraph_load_env_file "$CULTUREGRAPH_ROOT_ENV"
  culturegraph_load_env_file "$CULTUREGRAPH_API_ENV"
  culturegraph_load_env_file "$CULTUREGRAPH_WEB_ENV"

  unset PORT
  export API_HOST="${API_HOST:-0.0.0.0}"
  export API_PORT="${API_PORT:-8000}"
  export WEB_PORT="${WEB_PORT:-3000}"
  export DATABASE_URL="${DATABASE_URL:-postgresql://culturegraph:culturegraph@localhost:5432/culturegraph}"
  export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:8000}"
  export CORS_ORIGINS="${CORS_ORIGINS:-http://localhost:3000}"

  if [ "$API_PORT" = "5000" ] || [ "$WEB_PORT" = "5000" ]; then
    echo "Error: port 5000 is not used by CultureGraph. Set API_PORT=8000 and WEB_PORT=3000." >&2
    return 1 2>/dev/null || exit 1
  fi
}
