"""Admin dashboard query helpers."""

from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from app.models import Annotation, Artwork, CulturalEntity, ResearchNote, Visit

DEFAULT_ADMIN_LIMIT = 50
MAX_ADMIN_LIMIT = 200


def clamp_limit(limit: int) -> int:
    return max(1, min(limit, MAX_ADMIN_LIMIT))


def clamp_offset(offset: int) -> int:
    return max(0, offset)


def normalize_search(search: str | None) -> str | None:
    if search is None:
        return None
    cleaned = search.strip()
    return cleaned or None


def paginate(query: Query, *, limit: int, offset: int) -> tuple[list, int]:
    total = query.count()
    records = query.offset(offset).limit(limit).all()
    return records, total


def filter_visits(query: Query, search: str | None) -> Query:
    if not search:
        return query
    pattern = f"%{search}%"
    return query.filter(
        or_(
            Visit.museum_name.ilike(pattern),
            Visit.city.ilike(pattern),
            Visit.notes.ilike(pattern),
        )
    )


def filter_artworks(query: Query, search: str | None) -> Query:
    if not search:
        return query
    pattern = f"%{search}%"
    return query.filter(
        or_(
            Artwork.title.ilike(pattern),
            Artwork.artist.ilike(pattern),
            Artwork.museum_gallery.ilike(pattern),
            Artwork.personal_notes.ilike(pattern),
            Artwork.catalog_source.ilike(pattern),
        )
    )


def filter_annotations(query: Query, search: str | None) -> Query:
    if not search:
        return query
    pattern = f"%{search}%"
    return query.filter(
        or_(
            Annotation.text.ilike(pattern),
            Annotation.category.cast(str).ilike(pattern),
        )
    )


def filter_entities(query: Query, search: str | None) -> Query:
    if not search:
        return query
    pattern = f"%{search}%"
    return query.filter(
        or_(
            CulturalEntity.name.ilike(pattern),
            CulturalEntity.description.ilike(pattern),
            CulturalEntity.entity_type.cast(str).ilike(pattern),
        )
    )


def filter_research_notes(query: Query, search: str | None) -> Query:
    if not search:
        return query
    pattern = f"%{search}%"
    return query.filter(
        or_(
            ResearchNote.short_summary.ilike(pattern),
            ResearchNote.historical_context.ilike(pattern),
        )
    )


def count_all(db: Session) -> dict[str, int]:
    return {
        "visits": db.query(Visit).count(),
        "artworks": db.query(Artwork).count(),
        "annotations": db.query(Annotation).count(),
        "cultural_entities": db.query(CulturalEntity).count(),
        "research_notes": db.query(ResearchNote).count(),
    }
