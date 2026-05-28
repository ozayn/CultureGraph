"""Background AI enrichment after artwork capture."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Artwork, ResearchNote
from app.schemas import (
    ArtworkIdentificationRead,
    ArtworkLookupResponse,
    ResearchDraft,
    VisualAnalysisRead,
)
from app.services.artwork_identification import (
    build_identification,
    calibrate_research_draft,
    lookup_with_identification_candidates,
)
from app.services.artwork_lookup import lookup_artwork_candidates
from app.services.lookup_query import build_retrieval_lookup_query
from app.services.research import (
    ResearchConfigurationError,
    ResearchProviderError,
    get_research_provider,
    load_identification_meta,
    optional_meta_float,
    optional_meta_str,
    serialize_research_draft,
    strip_identification_meta,
)
from app.services.visual_analysis import VisualAnalysis
from app.services.lookup_response import lookup_response_from_result
from app.sources.routing import resolve_lookup_sources

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
        "label_image_url": artwork.label_image_url,
        "label_ocr_text": artwork.label_ocr_text,
    }


def _apply_artwork_label_ocr(draft: ResearchDraft, artwork: Artwork) -> ResearchDraft:
    from app.services.visual_analysis import extract_artist_from_ocr, extract_title_from_ocr

    label_text = (artwork.label_ocr_text or "").strip()
    if not label_text:
        return draft

    updated = draft.model_copy(deep=True)
    updated.ocr_label_text = label_text
    title = extract_title_from_ocr(label_text)
    artist = extract_artist_from_ocr(label_text)
    if title:
        updated.possible_title = title
    if artist:
        updated.possible_artist = artist
    return updated


def _build_lookup_response(db: Session, artwork: Artwork, draft: ResearchDraft) -> ArtworkLookupResponse:
    museum_name = artwork.visit.museum_name if artwork.visit else None
    built = build_retrieval_lookup_query(artwork, db, draft, museum_name=museum_name)

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

    return lookup_response_from_result(
        lookup_result,
        query=built.query,
        query_used=built.query_used,
        query_source=built.query_source,
        alternate_title=built.alternate_title,
        expected_medium_type=built.expected_medium_type,
        medium_type_filter=built.medium_type_filter,
        visual_keywords=built.query_source == "visual_keywords",
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
        draft = _apply_artwork_label_ocr(draft, artwork)

        _set_enrichment_state(
            artwork,
            status=ENRICHMENT_STATUS_RUNNING,
            stage=STAGE_SEARCHING_COLLECTIONS,
        )
        db.commit()
        db.refresh(artwork)

        lookup_response = _build_lookup_response(db, artwork, draft)
        visual = _draft_visual_analysis(draft)
        identification = build_identification(draft, lookup_response, visual)
        calibrated = calibrate_research_draft(draft, identification, visual)
        lookup_response = lookup_with_identification_candidates(lookup_response, identification)

        _set_enrichment_state(
            artwork,
            status=ENRICHMENT_STATUS_RUNNING,
            stage=STAGE_GENERATING_ANNOTATIONS,
        )
        db.commit()

        serialized = serialize_research_draft(calibrated)
        note = ResearchNote(artwork_id=artwork_id, **serialized)
        db.add(note)
        db.flush()

        artwork.enrichment_lookup = {
            "lookup": lookup_response.model_dump(mode="json"),
            "identification": ArtworkIdentificationRead.model_validate(
                identification.model_dump(mode="json")
            ).model_dump(mode="json"),
            "visual_analysis": (
                draft.visual_analysis.model_dump(mode="json") if draft.visual_analysis else None
            ),
        }

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


def _draft_visual_analysis(draft: ResearchDraft) -> VisualAnalysis | None:
    if not draft.visual_analysis:
        return None
    from app.services.visual_analysis import enrich_visual_analysis_fields

    visual = VisualAnalysis.model_validate(draft.visual_analysis.model_dump())
    return enrich_visual_analysis_fields(visual)


def parse_enrichment_payload(
    raw: dict | list | None,
) -> tuple[ArtworkLookupResponse | None, ArtworkIdentificationRead | None, VisualAnalysisRead | None]:
    if not raw or not isinstance(raw, dict):
        return None, None, None

    if "lookup" in raw:
        lookup_raw = raw.get("lookup")
        identification_raw = raw.get("identification")
        visual_raw = raw.get("visual_analysis")
        lookup = None
        identification = None
        visual = None
        try:
            if lookup_raw:
                lookup = ArtworkLookupResponse.model_validate(lookup_raw)
        except Exception:
            lookup = None
        try:
            if identification_raw:
                identification = ArtworkIdentificationRead.model_validate(identification_raw)
        except Exception:
            identification = None
        try:
            if visual_raw:
                visual = VisualAnalysisRead.model_validate(visual_raw)
        except Exception:
            visual = None
        return lookup, identification, visual

    try:
        return ArtworkLookupResponse.model_validate(raw), None, None
    except Exception:
        return None, None, None


def parse_enrichment_lookup(raw: dict | list | None) -> ArtworkLookupResponse | None:
    lookup, _, _ = parse_enrichment_payload(raw)
    return lookup


def enrichment_has_identification_block(raw: dict | list | None) -> bool:
    return isinstance(raw, dict) and "identification" in raw


def synthesize_legacy_identification(
    draft: ResearchDraft | None,
    *,
    existing: ArtworkIdentificationRead | None = None,
) -> ArtworkIdentificationRead | None:
    """Build an unverified visual-hypothesis identification from legacy draft fields."""
    if existing is not None:
        return existing
    if draft is None:
        return None

    from app.sources.matching import is_placeholder_artist, is_placeholder_title

    title = (draft.visual_hypothesis_title or draft.possible_title or "").strip() or None
    artist = (draft.visual_hypothesis_artist or draft.possible_artist or "").strip() or None

    if title and is_placeholder_title(title):
        title = None
    if artist and is_placeholder_artist(artist):
        artist = None
    if not title and not artist:
        return None

    title_bit = title or "Unknown title"
    artist_suffix = f" by {artist}" if artist else ""
    display = (
        f"AI visual hypothesis: {title_bit}{artist_suffix}. "
        "Not verified against collection records."
    )

    confidence = draft.visual_hypothesis_confidence or draft.confidence
    confidence_level = "medium" if confidence is not None and confidence >= 0.55 else "low"

    hypothesis_source = draft.hypothesis_source
    if not hypothesis_source:
        hypothesis_source = (
            "legacy" if draft.possible_title and not draft.visual_hypothesis_title else "vision"
        )

    return ArtworkIdentificationRead(
        identification_mode="style_subject",
        confidence_level=confidence_level,  # type: ignore[arg-type]
        display_summary=display,
        visual_hypothesis_title=title,
        visual_hypothesis_artist=artist,
        visual_hypothesis_confidence=confidence,
        visual_hypothesis_reason=draft.visual_hypothesis_reason,
        hypothesis_source=hypothesis_source,
        uncertainty_notes=[
            "Visual hypothesis only — confirm against a museum catalog record.",
        ],
    )


def resolve_enrichment_identification(
    artwork: Artwork,
    draft: ResearchDraft | None,
    identification: ArtworkIdentificationRead | None,
) -> ArtworkIdentificationRead | None:
    if enrichment_has_identification_block(artwork.enrichment_lookup):
        return identification
    return synthesize_legacy_identification(draft, existing=identification)


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

    visual_analysis: VisualAnalysisRead | None = None
    identification_meta: dict[str, str | float] = {}
    if getattr(note, "visual_analysis", None):
        try:
            parsed_visual = json.loads(note.visual_analysis)
            if isinstance(parsed_visual, dict):
                identification_meta = load_identification_meta(parsed_visual)
                visual_payload = strip_identification_meta(parsed_visual)
                visual_analysis = VisualAnalysisRead.model_validate(visual_payload)
        except (json.JSONDecodeError, ValueError):
            visual_analysis = None

    draft = ResearchDraft(
        short_summary=note.short_summary,
        historical_context=note.historical_context,
        visual_elements_to_notice=parse_json_list(note.visual_elements_to_notice),
        related_questions=parse_json_list(note.related_questions),
        suggested_annotations=load_note_suggestions(note),
        possible_title=note.possible_title,
        possible_artist=note.possible_artist,
        visual_hypothesis_title=optional_meta_str(identification_meta.get("visual_hypothesis_title")),
        visual_hypothesis_artist=optional_meta_str(identification_meta.get("visual_hypothesis_artist")),
        visual_hypothesis_confidence=optional_meta_float(
            identification_meta.get("visual_hypothesis_confidence")
        ),
        visual_hypothesis_reason=optional_meta_str(identification_meta.get("visual_hypothesis_reason")),
        hypothesis_source=optional_meta_str(identification_meta.get("hypothesis_source")),
        catalog_title=optional_meta_str(identification_meta.get("catalog_title")),
        catalog_artist=optional_meta_str(identification_meta.get("catalog_artist")),
        catalog_confidence=optional_meta_float(identification_meta.get("catalog_confidence")),
        period_or_movement=getattr(note, "period_or_movement", None),
        ocr_label_text=getattr(note, "ocr_label_text", None),
        confidence=getattr(note, "confidence", None),
        visual_analysis=visual_analysis,
    )
    return draft, note.id
