"""Orchestrate museum collection lookups for missing artwork images."""

from __future__ import annotations

from app.sources.base import ArtworkLookupCandidate, ArtworkLookupQuery
from app.sources.nga import search_nga_collection


class ArtworkLookupError(Exception):
    """Raised when lookup cannot be completed."""


def lookup_artwork_candidates(query: ArtworkLookupQuery) -> list[ArtworkLookupCandidate]:
    candidates: list[ArtworkLookupCandidate] = []

    nga_results = search_nga_collection(query)
    candidates.extend(nga_results)

    # Future: Smithsonian, Met, Art Institute of Chicago, Europeana adapters here.

    candidates.sort(key=lambda item: item.confidence, reverse=True)
    return candidates
