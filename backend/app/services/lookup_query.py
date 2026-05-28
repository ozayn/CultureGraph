"""Build artwork image lookup search terms from artwork metadata and AI/import hints."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from app.models import Artwork, CulturalEntity, CulturalEntityType, ResearchNote
from app.schemas import ResearchDraft
from app.services.lookup_medium import infer_expected_medium_type, resolve_medium_type_filter
from app.services.research import load_identification_meta
from app.services.visual_analysis import collect_visual_keywords, extract_title_from_ocr, visual_keywords_query
from app.sources.base import ArtworkLookupQuery
from app.sources.matching import is_placeholder_artist, is_placeholder_title, normalize

QuerySource = Literal[
    "manual",
    "ai_title",
    "saved_title",
    "artist_notes",
    "ocr_label",
    "visual_keywords",
]


@dataclass(frozen=True)
class BuiltLookupQuery:
    query: ArtworkLookupQuery
    query_used: str
    query_source: QuerySource
    artist_used: str | None
    alternate_title: str | None = None
    expected_medium_type: str = "unknown"
    medium_type_filter: str = "any"


def build_artwork_lookup_query(
    artwork: Artwork,
    db: Session,
    *,
    museum_name: str | None,
    title_override: str | None = None,
    artist_override: str | None = None,
    source: str | None = None,
    medium_type: str | None = None,
    medium_override: str | None = None,
) -> BuiltLookupQuery:
    ai_title, ai_artist, ai_medium = _latest_research_hints(db, artwork.id)
    expected_medium = infer_expected_medium_type(
        artwork_medium=artwork.medium,
        ai_medium=ai_medium,
        notes=artwork.personal_notes,
        medium_override=medium_override,
    )
    medium_filter = resolve_medium_type_filter(expected_medium, medium_type)
    medium_hint = (
        (medium_override or "").strip()
        or (artwork.medium or "").strip()
        or (ai_medium or "").strip()
        or None
    )
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
            expected_medium_type=expected_medium,
            medium_type_filter=medium_filter,
            medium_hint=medium_hint,
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
            expected_medium_type=expected_medium,
            medium_type_filter=medium_filter,
            medium_hint=medium_hint,
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
            expected_medium_type=expected_medium,
            medium_type_filter=medium_filter,
            medium_hint=medium_hint,
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
        expected_medium_type=expected_medium,
        medium_type_filter=medium_filter,
        medium_hint=medium_hint,
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
    expected_medium_type: str = "unknown",
    medium_type_filter: str = "any",
    medium_hint: str | None = None,
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
            expected_medium_type=expected_medium_type,
            medium_type_filter=medium_type_filter,
            medium_hint=medium_hint,
        ),
        query_used=query_used or "",
        query_source=query_source,
        artist_used=clean_artist,
        alternate_title=alternate_title,
        expected_medium_type=expected_medium_type,
        medium_type_filter=medium_type_filter,
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


def _latest_research_hints(db: Session, artwork_id: int) -> tuple[str | None, str | None, str | None]:
    note = (
        db.query(ResearchNote)
        .filter(ResearchNote.artwork_id == artwork_id)
        .order_by(ResearchNote.created_at.desc())
        .first()
    )
    if not note:
        return None, None, None

    meta: dict[str, str | float] = {}
    if getattr(note, "visual_analysis", None):
        try:
            parsed_visual = json.loads(note.visual_analysis)
            if isinstance(parsed_visual, dict):
                meta = load_identification_meta(parsed_visual)
        except json.JSONDecodeError:
            meta = {}

    title = note.possible_title or meta.get("visual_hypothesis_title")
    artist = note.possible_artist or meta.get("visual_hypothesis_artist")
    return (
        title.strip() if isinstance(title, str) and title.strip() else None,
        artist.strip() if isinstance(artist, str) and artist.strip() else None,
        _medium_from_research_note(note),
    )


def _medium_from_research_note(note: ResearchNote) -> str | None:
    try:
        annotations = json.loads(note.suggested_annotations or "[]")
    except json.JSONDecodeError:
        annotations = []
    if not isinstance(annotations, list):
        return None
    for item in annotations:
        if not isinstance(item, dict):
            continue
        if item.get("category") != "material":
            continue
        text = (item.get("note") or "").strip()
        if text:
            return text[:255]
    return None


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


def build_retrieval_lookup_query(
    artwork: Artwork,
    db: Session,
    draft: ResearchDraft,
    *,
    museum_name: str | None,
    medium_type: str | None = None,
    medium_override: str | None = None,
) -> BuiltLookupQuery:
    """Build collection search from OCR, saved metadata, visual hypotheses, and keywords."""
    from app.services.visual_analysis import VisualAnalysis

    visual = None
    if draft.visual_analysis:
        visual = VisualAnalysis.model_validate(draft.visual_analysis.model_dump())

    ai_medium = _medium_from_draft_annotations(draft)
    expected_medium = infer_expected_medium_type(
        artwork_medium=artwork.medium,
        ai_medium=ai_medium,
        notes=artwork.personal_notes,
        medium_override=medium_override,
    )
    medium_filter = resolve_medium_type_filter(expected_medium, medium_type)
    medium_hint = (
        (medium_override or "").strip()
        or (artwork.medium or "").strip()
        or (ai_medium or "").strip()
        or None
    )

    ocr_title = extract_title_from_ocr(draft.ocr_label_text)
    if ocr_title and not is_placeholder_title(ocr_title):
        artist = _resolve_artist(artwork.artist, draft.possible_artist, None)
        return _pack(
            artwork,
            museum_name,
            None,
            ocr_title,
            artist,
            query_source="ocr_label",
            expected_medium_type=expected_medium,
            medium_type_filter=medium_filter,
            medium_hint=medium_hint,
        )

    saved_title = (artwork.title or "").strip()
    if saved_title and not is_placeholder_title(saved_title):
        artist = _resolve_artist(artwork.artist, draft.possible_artist, None)
        return _pack(
            artwork,
            museum_name,
            None,
            saved_title,
            artist,
            query_source="saved_title",
            expected_medium_type=expected_medium,
            medium_type_filter=medium_filter,
            medium_hint=medium_hint,
        )

    if draft.possible_title and not is_placeholder_title(draft.possible_title):
        artist = _resolve_artist(artwork.artist, draft.possible_artist, None)
        return _pack(
            artwork,
            museum_name,
            None,
            draft.possible_title,
            artist,
            query_source="ocr_label" if draft.ocr_label_text else "ai_title",
            expected_medium_type=expected_medium,
            medium_type_filter=medium_filter,
            medium_hint=medium_hint,
        )

    hypothesis_title = (draft.visual_hypothesis_title or "").strip()
    if hypothesis_title and not is_placeholder_title(hypothesis_title):
        artist = _resolve_artist(
            artwork.artist,
            draft.visual_hypothesis_artist or draft.possible_artist,
            None,
        )
        return _pack(
            artwork,
            museum_name,
            None,
            hypothesis_title,
            artist,
            query_source="ai_title",
            expected_medium_type=expected_medium,
            medium_type_filter=medium_filter,
            medium_hint=medium_hint,
        )

    keywords = collect_visual_keywords(
        visual,
        period_or_movement=draft.period_or_movement,
        ocr_label_text=draft.ocr_label_text,
    )
    query_text = visual_keywords_query(keywords)
    if query_text:
        artist = _resolve_artist(artwork.artist, draft.possible_artist, None)
        return _pack(
            artwork,
            museum_name,
            None,
            query_text,
            artist,
            query_source="visual_keywords",
            expected_medium_type=expected_medium,
            medium_type_filter=medium_filter,
            medium_hint=medium_hint,
        )

    return build_artwork_lookup_query(
        artwork,
        db,
        museum_name=museum_name,
        medium_type=medium_type,
        medium_override=medium_override,
    )


def _medium_from_draft_annotations(draft: ResearchDraft) -> str | None:
    for item in draft.suggested_annotations:
        if item.category != "material":
            continue
        text = (item.note or "").strip()
        if text:
            return text[:255]
    return None
