"""National Gallery of Art open collection lookup (CC0 dataset)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.sources.routing import resolve_lookup_sources
from app.sources.base import ArtworkLookupCandidate, ArtworkLookupQuery
from app.sources.matching import resolve_search_terms, score_artwork_entry
from app.sources.museums import NGA_SOURCE_NAME, is_nga_museum

__all__ = [
    "NGA_SOURCE_NAME",
    "collect_nga_scored_candidates",
    "is_nga_museum",
    "search_nga_collection",
    "should_search_nga",
]

NGA_INDEX_PATH = Path(__file__).resolve().parent.parent / "data" / "nga_lookup_index.json"


def should_search_nga(query: ArtworkLookupQuery) -> bool:
    return "nga" in resolve_lookup_sources(query)


def collect_nga_scored_candidates(
    query: ArtworkLookupQuery,
) -> list[tuple[float, dict, ArtworkLookupCandidate]]:
    if not should_search_nga(query):
        return []

    search_text, artist_text = resolve_search_terms(query)
    if not search_text and not artist_text:
        return []

    scored: list[tuple[float, dict, ArtworkLookupCandidate]] = []
    for raw_entry in _load_index():
        entry = _normalize_nga_index_entry(raw_entry)
        score = score_artwork_entry(entry, search_text, artist_text, query.year_period)
        if score < 0.15:
            continue
        scored.append(
            (
                score,
                entry,
                ArtworkLookupCandidate(
                    title=entry["title"],
                    artist=entry.get("artist"),
                    date=entry.get("date"),
                    medium=entry.get("medium"),
                    image_url=entry.get("image_url"),
                    image_thumbnail_url=entry.get("image_thumbnail_url") or entry.get("image_url"),
                    object_url=entry.get("object_url"),
                    accession_number=entry.get("accession_number"),
                    source_name=NGA_SOURCE_NAME,
                    confidence=round(min(score, 0.95), 2),
                    rights_label=entry.get("rights_label"),
                    external_id=entry.get("object_id"),
                ),
            )
        )
    return scored


def search_nga_collection(
    query: ArtworkLookupQuery,
    *,
    limit: int = 8,
) -> list[ArtworkLookupCandidate]:
    scored = collect_nga_scored_candidates(query)
    scored.sort(key=lambda item: item[0], reverse=True)
    return [item[2] for item in scored[:limit]]


def _normalize_nga_index_entry(entry: dict) -> dict:
    """Legacy index rows may only store the IIIF thumb URL in image_url."""
    from app.services.artwork_image_urls import upgrade_nga_iiif_display_url

    thumb = (entry.get("image_thumbnail_url") or entry.get("image_url") or "").strip()
    display = (entry.get("image_url") or thumb).strip()
    if thumb and "api.nga.gov/iiif" in thumb:
        display = upgrade_nga_iiif_display_url(thumb) or display
        if display == thumb and "/full/!" in thumb:
            import re

            match = re.search(r"(https://api\.nga\.gov/iiif/[0-9a-f-]{36})", thumb)
            if match:
                display = f"{match.group(1)}/full/!1600,1600/0/default.jpg"
    normalized = dict(entry)
    normalized["image_url"] = display or thumb
    normalized["image_thumbnail_url"] = thumb or display
    return normalized


@lru_cache(maxsize=1)
def _load_index() -> tuple[dict, ...]:
    if not NGA_INDEX_PATH.is_file():
        return ()
    with NGA_INDEX_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        return ()
    return tuple(item for item in data if isinstance(item, dict))
