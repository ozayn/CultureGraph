"""Orchestrate museum collection lookups for missing artwork images."""

from __future__ import annotations

from app.services.lookup_ranking import rank_lookup_candidates
from app.sources.routing import resolve_lookup_sources
from app.sources.base import ArtworkLookupCandidate, ArtworkLookupQuery
from app.sources.nga import collect_nga_scored_candidates
from app.sources.smithsonian import collect_smithsonian_scored_candidates


class ArtworkLookupError(Exception):
    """Raised when lookup cannot be completed."""


def lookup_artwork_candidates(query: ArtworkLookupQuery) -> list[ArtworkLookupCandidate]:
    sources = resolve_lookup_sources(query)
    raw: list[tuple[float, dict, ArtworkLookupCandidate]] = []

    if "nga" in sources:
        raw.extend(collect_nga_scored_candidates(query))
    if "smithsonian" in sources:
        raw.extend(collect_smithsonian_scored_candidates(query))

    return rank_lookup_candidates(raw, query)
