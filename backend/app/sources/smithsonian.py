"""Smithsonian Open Access collection lookup (CC0 art museum units)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.sources.routing import resolve_lookup_sources
from app.sources.base import ArtworkLookupCandidate, ArtworkLookupQuery
from app.sources.matching import resolve_search_terms, score_artwork_entry
from app.sources.museums import is_smithsonian_museum

SMITHSONIAN_INDEX_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "smithsonian_lookup_index.json"
)

__all__ = ["is_smithsonian_museum", "search_smithsonian_collection", "should_search_smithsonian"]


def should_search_smithsonian(query: ArtworkLookupQuery) -> bool:
    return "smithsonian" in resolve_lookup_sources(query)


def search_smithsonian_collection(
    query: ArtworkLookupQuery,
    *,
    limit: int = 8,
) -> list[ArtworkLookupCandidate]:
    if not should_search_smithsonian(query):
        return []

    search_text, artist_text = resolve_search_terms(query)
    if not search_text and not artist_text:
        return []

    scored: list[tuple[float, dict]] = []
    for entry in _load_index():
        score = score_artwork_entry(entry, search_text, artist_text, query.year_period)
        if score >= 0.35:
            scored.append((score, entry))

    scored.sort(key=lambda item: item[0], reverse=True)
    results: list[ArtworkLookupCandidate] = []
    for score, entry in scored[:limit]:
        museum_name = entry.get("source_name") or "Smithsonian Open Access"
        results.append(
            ArtworkLookupCandidate(
                title=entry["title"],
                artist=entry.get("artist"),
                date=entry.get("date"),
                medium=entry.get("medium"),
                image_url=entry.get("image_url"),
                image_thumbnail_url=entry.get("image_thumbnail_url") or entry.get("image_url"),
                object_url=entry.get("object_url"),
                accession_number=entry.get("accession_number"),
                source_name=museum_name,
                confidence=round(min(score, 0.95), 2),
                rights_label=entry.get("rights_label"),
                external_id=entry.get("object_id"),
            )
        )
    return results


@lru_cache(maxsize=1)
def _load_index() -> tuple[dict, ...]:
    if not SMITHSONIAN_INDEX_PATH.is_file():
        return ()
    with SMITHSONIAN_INDEX_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        return ()
    return tuple(item for item in data if isinstance(item, dict))
