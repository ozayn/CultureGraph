"""Multi-stage museum lookup: exact → fuzzy → artist fallback → broad."""

from __future__ import annotations

from app.services.lookup_ranking import rank_lookup_candidates
from app.services.lookup_types import STRATEGY_ORDER, LookupResult, LookupStrategy
from app.sources.base import ArtworkLookupQuery
from app.sources.nga import collect_nga_scored_candidates
from app.sources.smithsonian import collect_smithsonian_scored_candidates


def lookup_artwork_candidates_staged(
    query: ArtworkLookupQuery,
    *,
    force_broad: bool = False,
) -> LookupResult:
    raw: list = []
    sources = _resolved_sources(query)
    if "nga" in sources:
        raw.extend(collect_nga_scored_candidates(query))
    if "smithsonian" in sources:
        raw.extend(collect_smithsonian_scored_candidates(query))

    if not raw:
        return LookupResult(candidates=[], query_strategy=None)

    strategies: tuple[LookupStrategy, ...] = ("broad",) if force_broad else STRATEGY_ORDER

    for strategy in strategies:
        candidates = rank_lookup_candidates(raw, query, strategy=strategy)
        if candidates:
            artist_fallback = strategy in {"artist_fallback", "broad"}
            return LookupResult(
                candidates=candidates,
                query_strategy=strategy,
                artist_fallback=artist_fallback,
            )

    return LookupResult(candidates=[], query_strategy=None)


def _resolved_sources(query: ArtworkLookupQuery) -> list[str]:
    from app.sources.routing import resolve_lookup_sources

    return resolve_lookup_sources(query)
