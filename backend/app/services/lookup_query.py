"""Build artwork image lookup search terms from artwork metadata and AI/import hints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from app.models import Artwork, CulturalEntity, CulturalEntityType, ResearchNote
from app.sources.base import ArtworkLookupQuery
from app.sources.matching import is_placeholder_artist, is_placeholder_title, normalize

QuerySource = Literal["manual", "ai_title", "saved_title", "artist_notes"]


@dataclass(frozen=True)
class BuiltLookupQuery:
    query: ArtworkLookupQuery
    query_used: str
    query_source: QuerySource
    artist_used: str | None
    alternate_title: str | None = None


def build_artwork_lookup_query(
    artwork: Artwork,
    db: Session,
    *,
    museum_name: str | None,
    title_override: str | None = None,
    artist_override: str | None = None,
    source: str | None = None,
) -> BuiltLookupQuery:
    ai_title, ai_artist = _latest_research_hints(db, artwork.id)
    import_title = _import_entity_title(db, artwork)

    if (title_override and title_override.strip()) or (artist_override and artist_override.strip()):
        title = (title_override or "").strip()
        if not title or is_placeholder_title(title):
            if ai_title and not is_placeholder_title(ai_title):
                title = ai_title
            elif saved := (artwork.title or "").strip():
                if not is_placeholder_title(saved):
                    title = saved
            elif import_title and not is_placeholder_title(import_title):
                title = import_title
            else:
                title = (artwork.personal_notes or "").strip()
        artist = _resolve_artist(artwork.artist, ai_artist, artist_override)
        return _pack(
            artwork,
            museum_name,
            source,
            title,
            artist,
            query_source="manual",
        )

    if ai_title and not is_placeholder_title(ai_title):
        artist = _resolve_artist(artwork.artist, ai_artist, artist_override)
        return _pack(
            artwork,
            museum_name,
            source,
            ai_title,
            artist,
            query_source="ai_title",
            alternate_title=_alternate_saved_title(artwork.title, ai_title, import_title),
        )

    saved_title = (artwork.title or "").strip()
    if saved_title and not is_placeholder_title(saved_title):
        artist = _resolve_artist(artwork.artist, ai_artist, artist_override)
        return _pack(
            artwork,
            museum_name,
            source,
            saved_title,
            artist,
            query_source="saved_title",
            alternate_title=import_title if import_title and import_title != saved_title else None,
        )

    artist = _resolve_artist(artwork.artist, ai_artist, artist_override)
    notes = (artwork.personal_notes or "").strip()
    title_from_notes = notes if notes else None
    return _pack(
        artwork,
        museum_name,
        source,
        title_from_notes or "",
        artist,
        query_source="artist_notes",
        alternate_title=import_title if import_title and not is_placeholder_title(import_title) else None,
    )


def _pack(
    artwork: Artwork,
    museum_name: str | None,
    source: str | None,
    title: str,
    artist: str | None,
    *,
    query_source: QuerySource,
    alternate_title: str | None = None,
) -> BuiltLookupQuery:
    clean_title = title.strip()
    clean_artist = artist.strip() if artist else None
    if clean_artist and is_placeholder_artist(clean_artist):
        clean_artist = None

    query_used = clean_title
    if not query_used and clean_artist:
        query_used = clean_artist
    elif query_used and clean_artist:
        query_used = f"{clean_title} · {clean_artist}"

    return BuiltLookupQuery(
        query=ArtworkLookupQuery(
            title=clean_title or None,
            artist=clean_artist,
            museum_name=museum_name,
            year_period=artwork.year_period,
            notes=artwork.personal_notes,
            source=source,
            has_title_query=bool(clean_title),
        ),
        query_used=query_used or "",
        query_source=query_source,
        artist_used=clean_artist,
        alternate_title=alternate_title,
    )


def _resolve_artist(
    saved: str | None,
    ai: str | None,
    override: str | None,
) -> str | None:
    if override and override.strip() and not is_placeholder_artist(override):
        return override.strip()
    if ai and not is_placeholder_artist(ai):
        return ai.strip()
    if saved and not is_placeholder_artist(saved):
        return saved.strip()
    return None


def _alternate_saved_title(
    saved: str | None,
    primary: str,
    import_title: str | None,
) -> str | None:
    if import_title and import_title != primary:
        return import_title
    saved_clean = (saved or "").strip()
    if saved_clean and saved_clean != primary and not is_placeholder_title(saved_clean):
        return saved_clean
    return None


def _latest_research_hints(db: Session, artwork_id: int) -> tuple[str | None, str | None]:
    note = (
        db.query(ResearchNote)
        .filter(ResearchNote.artwork_id == artwork_id)
        .order_by(ResearchNote.created_at.desc())
        .first()
    )
    if not note:
        return None, None
    title = getattr(note, "possible_title", None)
    artist = getattr(note, "possible_artist", None)
    return (
        title.strip() if title and title.strip() else None,
        artist.strip() if artist and artist.strip() else None,
    )


def _import_entity_title(db: Session, artwork: Artwork) -> str | None:
    if not artwork.visit_id:
        return None
    entities = (
        db.query(CulturalEntity)
        .filter(
            CulturalEntity.visit_id == artwork.visit_id,
            CulturalEntity.entity_type == CulturalEntityType.artwork,
        )
        .order_by(CulturalEntity.created_at.desc())
        .all()
    )
    saved_norm = normalize(artwork.title or "")
    for entity in entities:
        name = (entity.name or "").strip()
        if not name or is_placeholder_title(name):
            continue
        if saved_norm and normalize(name) == saved_norm:
            continue
        return name
    return None
