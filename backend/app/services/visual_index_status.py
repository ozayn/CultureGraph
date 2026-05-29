"""Visual index status helpers for admin and API responses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import CollectionArtwork, CollectionImageEmbedding
from app.services.visual_embedding import EMBEDDING_MODEL_KEY
from app.sources.museums import NGA_SOURCE_NAME

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
THUMBNAIL_CACHE_DIR = BACKEND_ROOT / "data" / "nga_thumbnail_cache"
STATE_FILE = BACKEND_ROOT / "data" / "nga_visual_index_state.json"


def collection_index_count(db: Session, *, source_name: str, embedding_model: str) -> int:
    return (
        db.query(CollectionImageEmbedding)
        .join(CollectionArtwork)
        .filter(
            CollectionArtwork.source_name == source_name,
            CollectionImageEmbedding.embedding_model == embedding_model,
        )
        .count()
    )


@dataclass(frozen=True)
class VisualIndexStatus:
    indexed_count: int
    embedding_model: str
    last_updated: datetime | None
    thumbnail_cache_size: int
    source_name: str = NGA_SOURCE_NAME


def thumbnail_cache_size_bytes() -> int:
    if not THUMBNAIL_CACHE_DIR.is_dir():
        return 0
    return sum(file_path.stat().st_size for file_path in THUMBNAIL_CACHE_DIR.rglob("*") if file_path.is_file())


def get_visual_index_status(db: Session) -> VisualIndexStatus:
    indexed_count = collection_index_count(
        db,
        source_name=NGA_SOURCE_NAME,
        embedding_model=EMBEDDING_MODEL_KEY,
    )
    last_updated = (
        db.query(func.max(CollectionImageEmbedding.created_at))
        .join(CollectionArtwork)
        .filter(
            CollectionArtwork.source_name == NGA_SOURCE_NAME,
            CollectionImageEmbedding.embedding_model == EMBEDDING_MODEL_KEY,
        )
        .scalar()
    )
    return VisualIndexStatus(
        indexed_count=indexed_count,
        embedding_model=EMBEDDING_MODEL_KEY,
        last_updated=last_updated,
        thumbnail_cache_size=thumbnail_cache_size_bytes(),
    )
