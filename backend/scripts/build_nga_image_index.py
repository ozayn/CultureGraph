#!/usr/bin/env python3
"""Build NGA collection artwork records and image embeddings for visual matching."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import settings
from app.database import SessionLocal
from app.services.nga_visual_index import BuildOptions, run_build
from app.services.visual_embedding import EMBEDDING_MODEL_KEY, VisualEmbeddingError

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build NGA collection thumbnails and image embeddings for visual matching."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum records to process in this run (default: NGA_INDEX_LIMIT or settings).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from the saved offset in data/nga_visual_index_state.json.",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Re-embed artworks even when embeddings already exist for the active model.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=25,
        help="Commit to the database and log progress every N records.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log planned work without writing embeddings or committing database changes.",
    )
    return parser.parse_args()


def resolve_limit(cli_limit: int | None) -> int:
    if cli_limit is not None:
        return max(1, cli_limit)
    env_limit = os.environ.get("NGA_INDEX_LIMIT")
    if env_limit:
        return max(1, int(env_limit))
    return max(1, settings.nga_index_limit)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = parse_args()
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be at least 1")

    options = BuildOptions(
        limit=resolve_limit(args.limit),
        resume=args.resume,
        rebuild=args.rebuild,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
    )

    db = SessionLocal()
    try:
        metrics = run_build(db, options)
    finally:
        db.close()

    elapsed = metrics.elapsed_seconds
    print(
        "Done. "
        f"processed={metrics.processed} "
        f"new_embeddings={metrics.new_embeddings} "
        f"reused={metrics.reused_embeddings} "
        f"skipped={metrics.skipped} "
        f"cache_hits={metrics.cache_hits} "
        f"downloads={metrics.downloads} "
        f"elapsed_s={elapsed:.1f}",
        flush=True,
    )


if __name__ == "__main__":
    os.environ.setdefault("VISUAL_EMBEDDING_BACKEND", "openclip")
    try:
        main()
    except VisualEmbeddingError as exc:
        raise SystemExit(str(exc)) from exc
