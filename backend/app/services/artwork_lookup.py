"""Orchestrate museum collection lookups for missing artwork images."""

from __future__ import annotations

from app.services.lookup_types import LookupResult
from app.services.lookup_stages import lookup_artwork_candidates_staged
from app.sources.base import ArtworkLookupCandidate, ArtworkLookupQuery


class ArtworkLookupError(Exception):
    """Raised when lookup cannot be completed."""


def lookup_artwork_candidates(
    query: ArtworkLookupQuery,
    *,
    force_broad: bool = False,
    allow_wikimedia_fallback: bool = False,
) -> LookupResult:
    return lookup_artwork_candidates_staged(
        query,
        force_broad=force_broad,
        allow_wikimedia_fallback=allow_wikimedia_fallback,
    )
