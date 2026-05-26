"""Orchestrate museum collection lookups for missing artwork images."""

from __future__ import annotations

from app.sources.routing import resolve_lookup_sources
from app.sources.base import ArtworkLookupCandidate, ArtworkLookupQuery
from app.sources.nga import search_nga_collection
from app.sources.smithsonian import search_smithsonian_collection


class ArtworkLookupError(Exception):
    """Raised when lookup cannot be completed."""


def lookup_artwork_candidates(query: ArtworkLookupQuery) -> list[ArtworkLookupCandidate]:
    sources = resolve_lookup_sources(query)
    candidates: list[ArtworkLookupCandidate] = []

    if "nga" in sources:
        candidates.extend(search_nga_collection(query))
    if "smithsonian" in sources:
        candidates.extend(search_smithsonian_collection(query))

    candidates.sort(key=lambda item: item.confidence, reverse=True)
    return candidates[:12]
