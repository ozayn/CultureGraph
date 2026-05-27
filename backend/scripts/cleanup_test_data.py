#!/usr/bin/env python3
"""Delete accidental pytest records from the local development database."""

from __future__ import annotations

import sys

from app.database import SessionLocal
from app.services.test_data_cleanup import cleanup_test_data


def main() -> int:
    db = SessionLocal()
    try:
        counts = cleanup_test_data(db)
    finally:
        db.close()

    print(
        "Removed test data from development database: "
        f"{counts['visits_deleted']} visit(s), "
        f"{counts['artworks_deleted']} artwork(s) (with annotations/research)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
