"""Background AI enrichment after artwork capture."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Artwork, ResearchNote
from app.schemas import ArtworkLookupResponse, ResearchDraft
from app.services.artwork_lookup import lookup_artwork_candidates
from app.services.lookup_query import build_artwork_lookup_query
from app.services.research import (
    ResearchConfigurationError,
    ResearchProviderError,
    get_research_provider,
    serialize_research_draft,
)
from app.sources.nga import should_search_nga
from app.sources.routing import resolve_lookup_sources, sources_searched_labels
from app.sources.smithsonian import should_search_smithsonian
from app.schemas import ArtworkLookupCandidateRead

logger = logging.getLogger(__name__)

ENRICHMENT_STATUS_IDLE = "idle"
ENRICHMENT_STATUS_PENDING = "pending"
ENRICHMENT_STATUS_RUNNING = "running"
ENRICHMENT_STATUS_COMPLETED = "completed"
ENRICHMENT_STATUS_FAILED = "failed"

STAGE_IDENTIFYING = "identifying"
STAGE_SEARCHING_COLLECTIONS = "searching_collections"
STAGE_GENERATING_ANNOTATIONS = "generating_annotations"


def _artwork_research_context(artwork: Artwork) -> dict[str, Any]:
    return {
        "title": artwork.title,
        "artist": artwork.artist,
        "year_period": artwork.year_period,
        "medium": artwork.medium,
        "museum_gallery": artwork.museum_gallery,
        "personal_notes": artwork.personal_notes,
        "image_url": artwork.image_url,
    }


def _build_lookup_response(db: Session, artwork: Artwork) -> ArtworkLookupResponse:
    museum_name = artwork.visit.museum_name if artwork.visit else None
    built = build_artwork_lookup_query(artwork, db, museum_name=museum_name)

    if not resolve_lookup_sources(built.query):
        return ArtworkLookupResponse(
            candidates=[],
            sources_searched=[],
            query_used=built.query_used,
            query_source=built.query_source,
            alternate_title=built.alternate_title,
            expected_medium_type=built.expected_medium_type,
            medium_type_filter=built.medium_type_filter,
        )

    lookup_result = lookup_artwork_candidates(built.query)
    candidates = lookup_result.candidates
    sources_searched = sources_searched_labels(built.query)

    notice: str | None = None
    if lookup_result.artist_fallback and candidates:
        artist_label = (built.query.artist or "").strip() or "this artist"
        notice = f"No exact title match found. Showing related works by {artist_label}."
    elif not candidates:
        if not built.query_used.strip():
            notice = "Add a title or artist to improve collection matching."
        elif should_search_smithsonian(built.query) and not should_search_nga(built.query):
            notice = "No close matches found in the Smithsonian Open Access index."
        elif should_search_nga(built.query) and not should_search_smithsonian(built.query):
            notice = "No close matches found in the National Gallery open collection index."
        else:
            notice = "No close matches found in the open collection indexes."

    return ArtworkLookupResponse(
        candidates=[
            ArtworkLookupCandidateRead.model_validate(item, from_attributes=True)
            for item in candidates
        ],
        sources_searched=sources_searched,
        query_used=built.query_used,
        query_source=built.query_source,
        query_strategy=lookup_result.query_strategy,
        artist_fallback=lookup_result.artist_fallback,
        alternate_title=built.alternate_title,
        expected_medium_type=built.expected_medium_type,
        medium_type_filter=built.medium_type_filter,
        notice=notice,
    )


def _set_enrichment_state(
    artwork: Artwork,
    *,
    status: str,
    stage: str | None = None,
    error: str | None = None,
) -> None:
    artwork.enrichment_status = status
    artwork.enrichment_stage = stage
    artwork.enrichment_error = error


def schedule_artwork_enrichment(artwork_id: int) -> None:
    """Fire-and-forget enrichment from sync request handlers."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(_run_enrichment_task(artwork_id))
        return

    loop.create_task(_run_enrichment_task(artwork_id))


async def _run_enrichment_task(artwork_id: int) -> None:
    db = SessionLocal()
    try:
        await run_artwork_enrichment(db, artwork_id)
    except Exception:
        logger.exception("artwork enrichment failed artwork_id=%s", artwork_id)
        artwork = db.get(Artwork, artwork_id)
        if artwork and artwork.enrichment_status != ENRICHMENT_STATUS_COMPLETED:
            _set_enrichment_state(
                artwork,
                status=ENRICHMENT_STATUS_FAILED,
                stage=None,
                error=artwork.enrichment_error or "Enrichment failed unexpectedly.",
            )
            db.commit()
    finally:
        db.close()


def request_artwork_enrichment(db: Session, artwork: Artwork) -> bool:
    """Mark artwork pending and schedule enrichment if eligible."""
    if not artwork.image_url:
        return False
    if artwork.enrichment_status in {
        ENRICHMENT_STATUS_PENDING,
        ENRICHMENT_STATUS_RUNNING,
    }:
        return False

    _set_enrichment_state(artwork, status=ENRICHMENT_STATUS_PENDING, stage=None, error=None)
    db.commit()
    db.refresh(artwork)
    schedule_artwork_enrichment(artwork.id)
    return True


async def run_artwork_enrichment(db: Session, artwork_id: int) -> None:
    artwork = db.get(Artwork, artwork_id)
    if not artwork:
        return

    if not artwork.image_url:
        _set_enrichment_state(
            artwork,
            status=ENRICHMENT_STATUS_IDLE,
            stage=None,
            error=None,
        )
        db.commit()
        return

    _set_enrichment_state(
        artwork,
        status=ENRICHMENT_STATUS_RUNNING,
        stage=STAGE_IDENTIFYING,
        error=None,
    )
    db.commit()

    try:
        provider = get_research_provider()
        draft = await provider.generate_research(_artwork_research_context(artwork))

        _set_enrichment_state(
            artwork,
            status=ENRICHMENT_STATUS_RUNNING,
            stage=STAGE_GENERATING_ANNOTATIONS,
        )
        db.commit()

        serialized = serialize_research_draft(draft)
        note = ResearchNote(artwork_id=artwork_id, **serialized)
        db.add(note)
        db.flush()

        _set_enrichment_state(
            artwork,
            status=ENRICHMENT_STATUS_RUNNING,
            stage=STAGE_SEARCHING_COLLECTIONS,
        )
        db.commit()
        db.refresh(artwork)

        lookup_response = _build_lookup_response(db, artwork)
        artwork.enrichment_lookup = lookup_response.model_dump(mode="json")

        _set_enrichment_state(
            artwork,
            status=ENRICHMENT_STATUS_COMPLETED,
            stage=None,
            error=None,
        )
        db.commit()
    except (ResearchConfigurationError, ResearchProviderError) as exc:
        _set_enrichment_state(
            artwork,
            status=ENRICHMENT_STATUS_FAILED,
            stage=None,
            error=str(exc),
        )
        db.commit()
        raise
    except Exception as exc:
        _set_enrichment_state(
            artwork,
            status=ENRICHMENT_STATUS_FAILED,
            stage=None,
            error="Could not complete AI enrichment.",
        )
        db.commit()
        raise exc


def parse_enrichment_lookup(raw: dict | list | None) -> ArtworkLookupResponse | None:
    if not raw or not isinstance(raw, dict):
        return None
    try:
        return ArtworkLookupResponse.model_validate(raw)
    except Exception:
        return None


def latest_research_draft(db: Session, artwork_id: int) -> tuple[ResearchDraft | None, int | None]:
    note = (
        db.query(ResearchNote)
        .filter(ResearchNote.artwork_id == artwork_id)
        .order_by(ResearchNote.created_at.desc())
        .first()
    )
    if not note:
        return None, None

    def parse_json_list(value: str) -> list[str]:
        try:
            parsed = json.loads(value)
            return [str(item) for item in parsed] if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return [line.strip() for line in value.splitlines() if line.strip()]

    from app.services.suggested_annotations import load_note_suggestions

    draft = ResearchDraft(
        short_summary=note.short_summary,
        historical_context=note.historical_context,
        visual_elements_to_notice=parse_json_list(note.visual_elements_to_notice),
        related_questions=parse_json_list(note.related_questions),
        suggested_annotations=load_note_suggestions(note),
        possible_title=note.possible_title,
        possible_artist=note.possible_artist,
    )
    return draft, note.id
