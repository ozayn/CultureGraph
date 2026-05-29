"""Museum-scoped visual similarity search over collection image embeddings."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models import Artwork, CollectionArtwork, CollectionImageEmbedding
from app.services.visual_embedding import (
    EMBEDDING_MODEL_KEY,
    VisualEmbeddingError,
    cosine_similarity,
    embed_image_path,
    resolve_artwork_image_path,
)
from app.sources.museums import NGA_SOURCE_NAME, is_nga_museum
from app.sources.routing import museum_collection_display_name
from app.sources.matching import artist_similarity, is_placeholder_artist, is_placeholder_title

logger = logging.getLogger(__name__)

INDEX_MISSING_NOTICE = (
    "Visual index not built yet. Run the NGA image index script: "
    "python scripts/build_nga_image_index.py"
)


@dataclass(frozen=True)
class VisualMatchCandidate:
    title: str
    artist: str | None
    date: str | None
    medium: str | None
    image_url: str | None
    thumbnail_url: str | None
    object_url: str | None
    source_name: str
    similarity_score: float
    confidence_label: str
    match_reason: str
    accession_number: str | None = None
    rights_label: str | None = None
    external_id: str | None = None
    metadata_boost: float = 0.0


@dataclass(frozen=True)
class VisualMatchResult:
    candidates: list[VisualMatchCandidate]
    source_name: str | None
    museum_collection_name: str | None
    search_scope: str
    embedding_model: str | None
    notice: str | None
    index_status: str
    query_image_url: str | None


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


def resolve_visual_match_source(museum_name: str | None) -> str | None:
    if is_nga_museum(museum_name):
        return NGA_SOURCE_NAME
    return None


def match_artwork_visually(db: Session, artwork: Artwork) -> VisualMatchResult:
    museum_name = artwork.visit.museum_name if artwork.visit else None
    source_name = resolve_visual_match_source(museum_name)
    collection_label = museum_collection_display_name(museum_name)

    if not artwork.image_url:
        return VisualMatchResult(
            candidates=[],
            source_name=source_name,
            museum_collection_name=collection_label,
            search_scope="none",
            embedding_model=EMBEDDING_MODEL_KEY,
            notice="Upload a photo before searching by visual similarity.",
            index_status="missing",
            query_image_url=None,
        )

    if not source_name:
        return VisualMatchResult(
            candidates=[],
            source_name=None,
            museum_collection_name=collection_label,
            search_scope="none",
            embedding_model=EMBEDDING_MODEL_KEY,
            notice="Visual matching is available for National Gallery of Art visits in this MVP.",
            index_status="missing",
            query_image_url=artwork.image_url,
        )

    indexed_count = collection_index_count(db, source_name=source_name, embedding_model=EMBEDDING_MODEL_KEY)
    if indexed_count == 0:
        return VisualMatchResult(
            candidates=[],
            source_name=source_name,
            museum_collection_name=collection_label,
            search_scope="museum",
            embedding_model=EMBEDDING_MODEL_KEY,
            notice=INDEX_MISSING_NOTICE,
            index_status="empty",
            query_image_url=artwork.image_url,
        )

    try:
        query_path = resolve_artwork_image_path(artwork.image_url)
        query_embedding = embed_image_path(query_path)
    except VisualEmbeddingError as exc:
        return VisualMatchResult(
            candidates=[],
            source_name=source_name,
            museum_collection_name=collection_label,
            search_scope="museum",
            embedding_model=EMBEDDING_MODEL_KEY,
            notice=str(exc),
            index_status="ready",
            query_image_url=artwork.image_url,
        )

    rows = (
        db.query(CollectionImageEmbedding)
        .join(CollectionArtwork)
        .options(joinedload(CollectionImageEmbedding.collection_artwork))
        .filter(
            CollectionArtwork.source_name == source_name,
            CollectionImageEmbedding.embedding_model == EMBEDDING_MODEL_KEY,
        )
        .all()
    )

    scored: list[tuple[float, CollectionArtwork, float, str]] = []
    for row in rows:
        record = row.collection_artwork
        visual_score = cosine_similarity(query_embedding, row.embedding_vector)
        metadata_boost, reason = _metadata_boost(artwork, record)
        combined = min(visual_score + metadata_boost, 0.99)
        scored.append((combined, record, visual_score, reason))

    scored.sort(key=lambda item: (item[0], item[2]), reverse=True)
    top_k = max(1, settings.visual_match_top_k)
    candidates = [
        _candidate_from_record(record, visual_score=visual_score, combined_score=combined, match_reason=reason)
        for combined, record, visual_score, reason in scored[:top_k]
    ]

    logger.info(
        "visual match artwork_id=%s source=%s indexed=%s returned=%s top=%.3f",
        artwork.id,
        source_name,
        indexed_count,
        len(candidates),
        candidates[0].similarity_score if candidates else 0.0,
    )

    return VisualMatchResult(
        candidates=candidates,
        source_name=source_name,
        museum_collection_name=collection_label,
        search_scope="museum",
        embedding_model=EMBEDDING_MODEL_KEY,
        notice=None,
        index_status="ready",
        query_image_url=artwork.image_url,
    )


def _metadata_boost(artwork: Artwork, record: CollectionArtwork) -> tuple[float, str]:
    boost = 0.0
    reasons: list[str] = ["Visual similarity"]

    saved_artist = (artwork.artist or "").strip()
    if saved_artist and not is_placeholder_artist(saved_artist) and record.artist:
        artist_score = artist_similarity(saved_artist, record.artist)
        if artist_score >= 0.72:
            boost += 0.04
            reasons.append("artist metadata")

    saved_title = (artwork.title or "").strip()
    if saved_title and not is_placeholder_title(saved_title) and record.title:
        if saved_title.lower() in record.title.lower() or record.title.lower() in saved_title.lower():
            boost += 0.03
            reasons.append("title hint")

    saved_medium = (artwork.medium or "").strip().lower()
    record_medium = (record.medium or "").strip().lower()
    if saved_medium and record_medium and saved_medium in record_medium:
        boost += 0.02
        reasons.append("medium hint")

    return min(boost, 0.08), ", ".join(reasons)


def _candidate_from_record(
    record: CollectionArtwork,
    *,
    visual_score: float,
    combined_score: float,
    match_reason: str,
) -> VisualMatchCandidate:
    if combined_score >= settings.visual_match_high_threshold:
        confidence_label = "high"
    elif combined_score >= settings.visual_match_possible_threshold:
        confidence_label = "possible"
    else:
        confidence_label = "weak"

    metadata = record.metadata_json if isinstance(record.metadata_json, dict) else {}
    accession = metadata.get("accession_number")

    return VisualMatchCandidate(
        title=record.title,
        artist=record.artist,
        date=record.date,
        medium=record.medium,
        image_url=record.image_url,
        thumbnail_url=record.thumbnail_url,
        object_url=record.object_url,
        source_name=record.source_name,
        similarity_score=round(combined_score, 4),
        confidence_label=confidence_label,
        match_reason=match_reason,
        accession_number=accession if isinstance(accession, str) else None,
        rights_label=record.rights_label,
        external_id=record.source_object_id,
    )
