"""Rank and filter museum lookup candidates for relevance."""

from __future__ import annotations

from app.services.lookup_types import LookupStrategy
from app.sources.base import ArtworkLookupCandidate, ArtworkLookupQuery
from app.sources.matching import score_artwork_entry_detailed

STRATEGY_THRESHOLDS: dict[LookupStrategy, dict[str, float]] = {
    "exact": {"low": 0.35, "high": 0.55, "min_title": 0.22, "min_artist": 0.35},
    "fuzzy": {"low": 0.28, "high": 0.48, "min_title": 0.15, "min_artist": 0.35},
    "artist_fallback": {"low": 0.24, "high": 0.42, "min_title": 0.0, "min_artist": 0.35},
    "broad": {"low": 0.18, "high": 0.35, "min_title": 0.0, "min_artist": 0.28},
}


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

    enriched: list[tuple[float, float, float, ArtworkLookupCandidate]] = []
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

        if score < low_min:
            continue
        if title_score < min_title and artist_score < min_artist:
            continue

        if has_title_query and strategy == "exact" and title_score < 0.22 and artist_score >= 0.4:
            score *= 0.55

        if title_score >= 0.88:
            score = min(score + 0.12, 0.98)
        elif title_score >= 0.65:
            score = min(score + 0.06, 0.95)
        if artist_score >= 0.75 and artist_text:
            score = min(score + 0.05, 0.98)

        low_confidence = score < high_min or (
            has_title_query and title_score < 0.32 and strategy in {"exact", "fuzzy"}
        )
        if strategy in {"artist_fallback", "broad"} and artist_score >= 0.4:
            low_confidence = score < high_min or (has_title_query and title_score < 0.2)

        enriched.append(
            (
                score,
                title_score,
                artist_score,
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
                ),
            )
        )

    if has_title_query and strategy in {"exact", "fuzzy"}:
        best_title = max((item[1] for item in enriched), default=0.0)
        if best_title >= 0.32:
            enriched = [
                item
                for item in enriched
                if item[1] >= 0.18 or (item[2] >= 0.42 and item[1] >= 0.1)
            ]

    enriched.sort(key=lambda item: (item[3].low_confidence, -item[0]))
    return [item[3] for item in enriched[:limit]]
