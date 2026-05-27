#!/usr/bin/env python3
"""Delete accidental pytest records from the repo root."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
VENV_PYTHON = BACKEND / ".venv" / "bin" / "python"
TARGET = BACKEND / "scripts" / "cleanup_test_data.py"


def main() -> int:
    if not TARGET.is_file():
        print(f"Missing cleanup script: {TARGET}", file=sys.stderr)
        return 1

    if not VENV_PYTHON.is_file():
        print("Backend venv not found. Run ./scripts/dev.sh once to create it.", file=sys.stderr)
        return 1

    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND)
    result = subprocess.run(
        [str(VENV_PYTHON), str(TARGET)],
        cwd=BACKEND,
        env=env,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
