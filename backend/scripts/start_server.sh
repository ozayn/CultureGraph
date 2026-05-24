#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export PYTHONPATH=.

python -c "from app.db_startup import prepare_database; prepare_database()"

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
