"""Detect database upload paths whose files are missing on disk."""

from __future__ import annotations

from typing import Any, Literal

from sqlalchemy.orm import Session

from app.models import Artwork, AudioNote, CulturalEntity
from app.services.artwork_image_urls import is_upload_path, upload_file_exists
from app.services.upload_storage import get_upload_storage

UploadRecordType = Literal["artwork", "cultural_entity", "audio_note"]


def _append_missing(
    items: list[dict[str, Any]],
    *,
    record_type: UploadRecordType,
    record_id: int,
    field: str,
    path: str,
    label: str | None,
    limit: int,
) -> bool:
    if len(items) >= limit:
        return False
    if not is_upload_path(path) or upload_file_exists(path, get_upload_storage().upload_root()):
        return True
    items.append(
        {
            "record_type": record_type,
            "record_id": record_id,
            "field": field,
            "path": path.strip(),
            "label": label,
        }
    )
    return True


def collect_missing_upload_records(db: Session, *, limit: int = 200) -> list[dict[str, Any]]:
    missing: list[dict[str, Any]] = []

    artwork_fields = (
        "image_url",
        "image_master_url",
        "image_thumbnail_url",
        "label_image_url",
        "label_image_thumbnail_url",
    )
    for artwork in db.query(Artwork).order_by(Artwork.id.asc()):
        label = artwork.title or f"Artwork #{artwork.id}"
        for field in artwork_fields:
            value = getattr(artwork, field)
            if not value:
                continue
            if not _append_missing(
                missing,
                record_type="artwork",
                record_id=artwork.id,
                field=field,
                path=value,
                label=label,
                limit=limit,
            ):
                return missing

    for entity in db.query(CulturalEntity).order_by(CulturalEntity.id.asc()):
        label = entity.name
        for field in ("image_url", "thumbnail_url"):
            value = getattr(entity, field)
            if not value:
                continue
            if not _append_missing(
                missing,
                record_type="cultural_entity",
                record_id=entity.id,
                field=field,
                path=value,
                label=label,
                limit=limit,
            ):
                return missing

    for note in db.query(AudioNote).order_by(AudioNote.id.asc()):
        if not _append_missing(
            missing,
            record_type="audio_note",
            record_id=note.id,
            field="audio_url",
            path=note.audio_url,
            label=f"Audio note #{note.id}",
            limit=limit,
        ):
            return missing

    return missing


def count_missing_upload_records(db: Session) -> int:
    return len(collect_missing_upload_records(db, limit=10_000))
