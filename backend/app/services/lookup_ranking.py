"""Rank and filter museum lookup candidates for relevance."""

from __future__ import annotations

from app.sources.base import ArtworkLookupCandidate, ArtworkLookupQuery
from app.sources.matching import score_artwork_entry_detailed

HIGH_CONFIDENCE_MIN = 0.55
LOW_CONFIDENCE_MIN = 0.35


def rank_lookup_candidates(
    raw: list[tuple[float, dict, ArtworkLookupCandidate]],
    query: ArtworkLookupQuery,
    *,
    limit: int = 12,
) -> list[ArtworkLookupCandidate]:
    if not raw:
        return []

    has_title_query = bool(query.has_title_query and (query.title or "").strip())
    search_text = (query.title or "").strip()
    artist_text = (query.artist or "").strip()

    enriched: list[tuple[float, float, float, ArtworkLookupCandidate]] = []
    for combined, entry, candidate in raw:
        details = score_artwork_entry_detailed(
            entry, search_text, artist_text, query.year_period
        )
        score = details.combined
        title_score = details.title_score
        artist_score = details.artist_score

        if score < LOW_CONFIDENCE_MIN:
            continue
        if title_score < 0.12 and artist_score < 0.22:
            continue
        if has_title_query and title_score < 0.22 and artist_score >= 0.35:
            score *= 0.55

        if title_score >= 0.88:
            score = min(score + 0.12, 0.98)
        elif title_score >= 0.72:
            score = min(score + 0.06, 0.95)
        if artist_score >= 0.75 and artist_text:
            score = min(score + 0.05, 0.98)

        low_confidence = score < HIGH_CONFIDENCE_MIN or (
            has_title_query and title_score < 0.32
        )
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

    if has_title_query:
        best_title = max((item[1] for item in enriched), default=0.0)
        if best_title >= 0.32:
            enriched = [
                item
                for item in enriched
                if item[1] >= 0.22 or (item[2] >= 0.45 and item[1] >= 0.12)
            ]

    enriched.sort(key=lambda item: (item[3].low_confidence, -item[0]))
    return [item[3] for item in enriched[:limit]]
