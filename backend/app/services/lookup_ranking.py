"""Rank and filter museum lookup candidates for relevance."""

from __future__ import annotations

from typing import Literal

from app.services.lookup_medium import (
    build_match_reasons,
    classify_medium,
    medium_score_adjustment,
    medium_type_label,
    mediums_match,
)
from app.services.lookup_types import LookupStrategy
from app.sources.base import ArtworkLookupCandidate, ArtworkLookupQuery
from app.sources.matching import (
    is_attribution_artist,
    is_placeholder_artist,
    passes_title_specific_gate,
    score_artwork_entry_detailed,
)

MatchTier = Literal["high", "possible", "weak"]

HIGH_CONFIDENCE_MIN = 0.85
POSSIBLE_CONFIDENCE_MIN = 0.70

STRATEGY_THRESHOLDS: dict[LookupStrategy, dict[str, float]] = {
    "exact": {"low": 0.48, "high": 0.70, "min_title": 0.32, "min_artist": 0.48},
    "fuzzy": {"low": 0.42, "high": 0.65, "min_title": 0.24, "min_artist": 0.42},
    "artist_fallback": {"low": 0.38, "high": 0.58, "min_title": 0.0, "min_artist": 0.48},
    "broad": {"low": 0.35, "high": 0.55, "min_title": 0.0, "min_artist": 0.42},
}


def confidence_to_match_tier(
    confidence: float,
    *,
    title_score: float,
    artist_score: float,
    attribution: bool,
) -> MatchTier:
    if confidence >= HIGH_CONFIDENCE_MIN and title_score >= 0.45:
        return "high"
    if confidence >= POSSIBLE_CONFIDENCE_MIN:
        if attribution:
            return "weak"
        if title_score < 0.22 and artist_score < 0.65:
            return "weak"
        return "possible"
    return "weak"


def partition_lookup_candidates(
    candidates: list[ArtworkLookupCandidate],
) -> tuple[list[ArtworkLookupCandidate], list[ArtworkLookupCandidate]]:
    primary = [candidate for candidate in candidates if candidate.match_tier in {"high", "possible"}]
    related = [candidate for candidate in candidates if candidate.match_tier == "weak"]
    return primary, related


def rank_lookup_candidates(
    raw: list[tuple[float, dict, ArtworkLookupCandidate]],
    query: ArtworkLookupQuery,
    *,
    strategy: LookupStrategy = "exact",
    limit: int = 12,
) -> list[ArtworkLookupCandidate]:
    if not raw:
        return []

    thresholds = STRATEGY_THRESHOLDS[strategy]
    low_min = thresholds["low"]
    high_min = thresholds["high"]
    min_title = thresholds["min_title"]
    min_artist = thresholds["min_artist"]
    strict_artist = strategy in {"exact", "fuzzy"}

    has_title_query = bool(query.has_title_query and (query.title or "").strip())
    search_text = (query.title or "").strip()
    artist_text = (query.artist or "").strip()
    notes_text = (query.notes or "").strip()
    expected_medium = query.expected_medium_type or "unknown"
    medium_filter = query.medium_type_filter or "any"

    enriched: list[tuple[float, float, float, bool, bool, MatchTier, ArtworkLookupCandidate]] = []
    for _combined, entry, candidate in raw:
        details = score_artwork_entry_detailed(
            entry,
            search_text,
            artist_text,
            query.year_period,
            strict_artist_gate=strict_artist,
        )
        title_score = details.title_score
        artist_score = details.artist_score
        score = details.combined

        if strategy == "artist_fallback":
            if artist_score < min_artist:
                continue
            title_score = score_artwork_entry_detailed(
                entry, search_text, "", query.year_period, strict_artist_gate=False
            ).title_score
            keyword_score = 0.0
            if notes_text:
                keyword_score = score_artwork_entry_detailed(
                    entry, notes_text, "", query.year_period, strict_artist_gate=False
                ).title_score
            title_score = max(title_score, keyword_score)
            score = title_score * 0.58 + artist_score * 0.42

        if strategy == "broad":
            if artist_score < min_artist and title_score < min_title:
                continue
            score = max(score, title_score * 0.5 + artist_score * 0.5)

        if has_title_query and strategy in {"exact", "fuzzy"}:
            if not passes_title_specific_gate(
                search_text=search_text,
                artist_text=artist_text,
                entry=entry,
                title_score=title_score,
                artist_score=artist_score,
            ):
                continue

        if score < low_min:
            continue
        if title_score < min_title and artist_score < min_artist:
            continue

        if has_title_query and strategy == "exact" and title_score < 0.28 and artist_score < 0.72:
            continue

        if title_score >= 0.88:
            score = min(score + 0.12, 0.98)
        elif title_score >= 0.65:
            score = min(score + 0.06, 0.95)
        if artist_score >= 0.78 and artist_text and not is_attribution_artist(entry.get("artist") or ""):
            score = min(score + 0.05, 0.98)
        elif is_attribution_artist(entry.get("artist") or ""):
            score = min(score, 0.62)

        candidate_medium_type = classify_medium(candidate.medium)
        if medium_filter in {"2d", "3d"} and candidate_medium_type != medium_filter:
            continue

        relevant_for_medium = artist_score >= 0.55
        if relevant_for_medium and expected_medium != "unknown":
            medium_match = mediums_match(expected_medium, candidate_medium_type)
            score = min(
                max(score + medium_score_adjustment(expected_medium, candidate_medium_type), 0.0),
                0.98,
            )
            medium_mismatch = medium_match is False
        else:
            medium_match = None
            medium_mismatch = False

        attribution = is_attribution_artist(entry.get("artist") or "")
        match_tier = confidence_to_match_tier(
            score,
            title_score=title_score,
            artist_score=artist_score,
            attribution=attribution,
        )
        if strategy in {"artist_fallback", "broad"} and artist_score >= 0.78 and title_score < 0.35:
            match_tier = "possible" if score >= POSSIBLE_CONFIDENCE_MIN else "weak"
        low_confidence = match_tier == "weak" or medium_mismatch

        match_reasons = build_match_reasons(
            title_score=title_score,
            artist_score=artist_score,
            medium_match=medium_match,
            has_title_query=has_title_query,
            artist_text=artist_text,
        )
        if candidate_medium_type != "unknown":
            match_reasons = [
                *match_reasons,
                medium_type_label(candidate_medium_type),
            ][:5]

        enriched.append(
            (
                score,
                title_score,
                artist_score,
                medium_mismatch,
                low_confidence,
                match_tier,
                ArtworkLookupCandidate(
                    title=candidate.title,
                    artist=candidate.artist,
                    date=candidate.date,
                    medium=candidate.medium,
                    image_url=candidate.image_url,
                    image_thumbnail_url=candidate.image_thumbnail_url,
                    object_url=candidate.object_url,
                    accession_number=candidate.accession_number,
                    source_name=candidate.source_name,
                    confidence=round(min(score, 0.98), 2),
                    rights_label=candidate.rights_label,
                    external_id=candidate.external_id,
                    low_confidence=low_confidence,
                    medium_type=candidate_medium_type,
                    medium_match=medium_match,
                    match_reasons=tuple(match_reasons),
                    match_tier=match_tier,
                ),
            )
        )

    if has_title_query and strategy in {"exact", "fuzzy"}:
        best_title = max((item[1] for item in enriched), default=0.0)
        if best_title >= 0.32:
            enriched = [
                item
                for item in enriched
                if item[1] >= 0.22
                or (item[2] >= 0.72 and item[1] >= 0.12)
                or item[5] == "high"
            ]

    enriched.sort(
        key=lambda item: (
            item[3],
            item[5] == "weak",
            item[5] == "possible",
            -item[0],
        )
    )
    if medium_filter in {"2d", "3d"}:
        return [item[6] for item in enriched[:limit]]

    matched = [item for item in enriched if not item[3]]
    mismatched = [item for item in enriched if item[3]]
    selected = matched[:limit]
    if mismatched and expected_medium != "unknown":
        reserve = min(2, max(1, limit // 5))
        selected.extend(mismatched[:reserve])
    return [item[6] for item in selected]
