"""Bulk delete helpers for the admin dashboard."""

from __future__ import annotations

from typing import TypeVar

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Annotation, Artwork, CulturalEntity, ResearchNote, Visit
from app.services.record_cleanup import delete_artwork, delete_visit

T = TypeVar("T")

MAX_BULK_DELETE = 200


def _validate_ids(ids: list[int]) -> list[int]:
    if not ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one ID is required.",
        )
    unique = list(dict.fromkeys(ids))
    if len(unique) > MAX_BULK_DELETE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete more than {MAX_BULK_DELETE} records at once.",
        )
    if any(item <= 0 for item in unique):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="All IDs must be positive integers.",
        )
    return unique


def _load_or_error(db: Session, model: type[T], ids: list[int]) -> list[T]:
    records = db.query(model).filter(model.id.in_(ids)).all()
    found_ids = {record.id for record in records}
    missing = [item for item in ids if item not in found_ids]
    if missing:
        missing_text = ", ".join(str(item) for item in missing)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No matching {model.__tablename__} records for ID(s): {missing_text}.",
        )
    by_id = {record.id: record for record in records}
    return [by_id[item] for item in ids]


def bulk_delete_visits(db: Session, ids: list[int]) -> int:
    validated = _validate_ids(ids)
    visits = _load_or_error(db, Visit, validated)
    for visit in visits:
        delete_visit(db, visit)
    db.commit()
    return len(visits)


def bulk_delete_artworks(db: Session, ids: list[int]) -> int:
    validated = _validate_ids(ids)
    artworks = _load_or_error(db, Artwork, validated)
    for artwork in artworks:
        delete_artwork(db, artwork)
    db.commit()
    return len(artworks)


def bulk_delete_annotations(db: Session, ids: list[int]) -> int:
    validated = _validate_ids(ids)
    annotations = _load_or_error(db, Annotation, validated)
    for annotation in annotations:
        db.delete(annotation)
    db.commit()
    return len(annotations)


def bulk_delete_entities(db: Session, ids: list[int]) -> int:
    validated = _validate_ids(ids)
    entities = _load_or_error(db, CulturalEntity, validated)
    for entity in entities:
        db.delete(entity)
    db.commit()
    return len(entities)


def bulk_delete_research_notes(db: Session, ids: list[int]) -> int:
    validated = _validate_ids(ids)
    notes = _load_or_error(db, ResearchNote, validated)
    for note in notes:
        db.delete(note)
    db.commit()
    return len(notes)
