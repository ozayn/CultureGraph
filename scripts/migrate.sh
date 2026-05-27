#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/backend"

if [ ! -d ".venv" ]; then
  echo "Backend venv not found. Run ./scripts/dev.sh once to create it."
  exit 1
fi

# shellcheck disable=SC1091
source ".venv/bin/activate"

echo "Running Alembic migrations (backend venv) …"
alembic upgrade head
