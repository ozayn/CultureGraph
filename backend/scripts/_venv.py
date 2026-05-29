"""Re-run project scripts with backend/.venv when shell aliases bypass activation."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def reexec_with_project_venv() -> None:
    backend_root = Path(__file__).resolve().parent.parent
    venv_root = backend_root / ".venv"
    venv_python = venv_root / "bin" / "python"
    if not venv_python.is_file():
        return
    if Path(sys.prefix).resolve() == venv_root.resolve():
        return
    os.execv(str(venv_python), [str(venv_python), *sys.argv])
