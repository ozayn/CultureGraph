#!/usr/bin/env python3
"""Build NGA collection artwork records and image embeddings for visual matching."""

from __future__ import annotations

import json
import os
import sys
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image
from sqlalchemy.orm import Session

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import settings
from app.database import SessionLocal
from app.models import CollectionArtwork, CollectionImageEmbedding
from app.services.visual_embedding import EMBEDDING_MODEL_KEY, VisualEmbeddingError, embed_pil_image
from app.sources.museums import NGA_SOURCE_NAME

NGA_LOOKUP_INDEX = BACKEND_ROOT / "app" / "data" / "nga_lookup_index.json"
THUMB_TIMEOUT = 20


def _load_records(limit: int) -> list[dict]:
    if not NGA_LOOKUP_INDEX.is_file():
        raise SystemExit(
            f"Missing {NGA_LOOKUP_INDEX}. Run scripts/build_nga_lookup_index.py first."
        )
    records = json.loads(NGA_LOOKUP_INDEX.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise SystemExit("NGA lookup index must be a JSON list.")
    return [record for record in records if isinstance(record, dict)][:limit]


def _upsert_artwork(db: Session, record: dict) -> CollectionArtwork:
    object_id = str(record.get("object_id") or "").strip()
    title = (record.get("title") or "").strip()
    if not object_id or not title:
        raise ValueError("Record missing object_id or title")

    existing = (
        db.query(CollectionArtwork)
        .filter(
            CollectionArtwork.source_name == NGA_SOURCE_NAME,
            CollectionArtwork.source_object_id == object_id,
        )
        .one_or_none()
    )
    payload = {
        "title": title,
        "artist": record.get("artist"),
        "date": record.get("date"),
        "medium": record.get("medium"),
        "image_url": record.get("image_url"),
        "thumbnail_url": record.get("image_thumbnail_url") or record.get("image_url"),
        "object_url": record.get("object_url"),
        "rights_label": record.get("rights_label"),
        "metadata_json": {
            "accession_number": record.get("accession_number"),
            "begin_year": record.get("begin_year"),
            "end_year": record.get("end_year"),
        },
    }
    if existing:
        for key, value in payload.items():
            setattr(existing, key, value)
        return existing

    artwork = CollectionArtwork(
        source_name=NGA_SOURCE_NAME,
        source_object_id=object_id,
        **payload,
    )
    db.add(artwork)
    db.flush()
    return artwork


def _download_image(url: str | None) -> Image.Image | None:
    if not url or not url.strip():
        return None
    try:
        response = requests.get(url, timeout=THUMB_TIMEOUT)
        response.raise_for_status()
        return Image.open(BytesIO(response.content))
    except Exception:
        return None


def _ensure_embedding(db: Session, artwork: CollectionArtwork, image: Image.Image, image_url: str) -> bool:
    existing = (
        db.query(CollectionImageEmbedding)
        .filter(
            CollectionImageEmbedding.collection_artwork_id == artwork.id,
            CollectionImageEmbedding.embedding_model == EMBEDDING_MODEL_KEY,
        )
        .one_or_none()
    )
    if existing:
        return False

    vector = embed_pil_image(image)
    db.add(
        CollectionImageEmbedding(
            collection_artwork_id=artwork.id,
            embedding_model=EMBEDDING_MODEL_KEY,
            embedding_vector=vector,
            image_url=image_url,
        )
    )
    return True


def main() -> None:
    limit = int(os.environ.get("NGA_INDEX_LIMIT", settings.nga_index_limit))
    records = _load_records(limit)
    print(f"Indexing up to {len(records)} NGA records with model {EMBEDDING_MODEL_KEY}")

    db = SessionLocal()
    created_embeddings = 0
    skipped = 0
    try:
        for index, record in enumerate(records, start=1):
            try:
                artwork = _upsert_artwork(db, record)
            except ValueError:
                skipped += 1
                continue

            image_url = artwork.thumbnail_url or artwork.image_url
            image = _download_image(image_url)
            if image is None:
                skipped += 1
                continue

            if _ensure_embedding(db, artwork, image, image_url or ""):
                created_embeddings += 1

            if index % 25 == 0:
                db.commit()
                print(f"processed={index} new_embeddings={created_embeddings} skipped={skipped}")

        db.commit()
    finally:
        db.close()

    print(
        f"Done. records={len(records)} new_embeddings={created_embeddings} skipped={skipped}"
    )


if __name__ == "__main__":
    os.environ.setdefault("VISUAL_EMBEDDING_BACKEND", "openclip")
    try:
        main()
    except VisualEmbeddingError as exc:
        raise SystemExit(str(exc)) from exc
