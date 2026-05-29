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


def count_missing_upload_record_ids(db: Session) -> int:
    missing = collect_missing_upload_records(db, limit=10_000)
    return len({(item["record_type"], item["record_id"]) for item in missing})


def summarize_missing_upload_records(
    db: Session,
    *,
    sample_limit: int = 100,
) -> tuple[list[dict[str, Any]], int, int]:
    missing = collect_missing_upload_records(db, limit=10_000)
    record_count = len({(item["record_type"], item["record_id"]) for item in missing})
    return missing[:sample_limit], len(missing), record_count


def clear_missing_upload_references(db: Session) -> tuple[int, int]:
    """Null out broken upload paths. Audio notes with missing files are removed."""
    missing = collect_missing_upload_records(db, limit=10_000)
    if not missing:
        return 0, 0

    artwork_fields: dict[int, set[str]] = {}
    entity_fields: dict[int, set[str]] = {}
    audio_note_ids: set[int] = set()

    for item in missing:
        record_type = item["record_type"]
        record_id = item["record_id"]
        field = item["field"]
        if record_type == "artwork":
            artwork_fields.setdefault(record_id, set()).add(field)
        elif record_type == "cultural_entity":
            entity_fields.setdefault(record_id, set()).add(field)
        elif record_type == "audio_note" and field == "audio_url":
            audio_note_ids.add(record_id)

    for artwork_id, fields in artwork_fields.items():
        artwork = db.get(Artwork, artwork_id)
        if not artwork:
            continue
        for field in fields:
            if field in {
                "image_url",
                "image_master_url",
                "image_thumbnail_url",
                "label_image_url",
                "label_image_thumbnail_url",
            }:
                setattr(artwork, field, None)

    for entity_id, fields in entity_fields.items():
        entity = db.get(CulturalEntity, entity_id)
        if not entity:
            continue
        for field in fields:
            if field in {"image_url", "thumbnail_url"}:
                setattr(entity, field, None)

    for note_id in audio_note_ids:
        note = db.get(AudioNote, note_id)
        if note:
            db.delete(note)

    db.commit()

    affected_records = len(artwork_fields) + len(entity_fields) + len(audio_note_ids)
    return len(missing), affected_records
