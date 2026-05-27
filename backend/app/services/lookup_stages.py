"""Multi-stage museum lookup: exact → fuzzy → artist fallback → broad."""

from __future__ import annotations

from app.services.lookup_ranking import rank_lookup_candidates
from app.services.lookup_types import STRATEGY_ORDER, LookupResult, LookupStrategy
from app.sources.aic import collect_aic_scored_candidates
from app.sources.base import ArtworkLookupQuery
from app.sources.met import collect_met_scored_candidates
from app.sources.nga import collect_nga_scored_candidates
from app.sources.smithsonian import collect_smithsonian_scored_candidates
from app.sources.wikimedia import collect_wikimedia_scored_candidates


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
    if "met" in sources:
        raw.extend(collect_met_scored_candidates(query))
    if "aic" in sources:
        raw.extend(collect_aic_scored_candidates(query))

    result = _rank_staged(raw, query, force_broad=force_broad)
    if result.candidates:
        return result

    wiki_raw = collect_wikimedia_scored_candidates(_wikimedia_fallback_query(query))
    if wiki_raw:
        return _rank_staged(wiki_raw, query, force_broad=True, wikimedia_fallback=True)

    return LookupResult(candidates=[], query_strategy=None)


def _rank_staged(
    raw: list,
    query: ArtworkLookupQuery,
    *,
    force_broad: bool = False,
    wikimedia_fallback: bool = False,
) -> LookupResult:
    if not raw:
        return LookupResult(candidates=[], query_strategy=None)

    strategies: tuple[LookupStrategy, ...] = ("broad",) if force_broad else STRATEGY_ORDER

    for strategy in strategies:
        candidates = rank_lookup_candidates(raw, query, strategy=strategy)
        if candidates:
            artist_fallback = strategy in {"artist_fallback", "broad"} or wikimedia_fallback
            return LookupResult(
                candidates=candidates,
                query_strategy=strategy,
                artist_fallback=artist_fallback,
            )

    return LookupResult(candidates=[], query_strategy=None)


def _wikimedia_fallback_query(query: ArtworkLookupQuery) -> ArtworkLookupQuery:
    return ArtworkLookupQuery(
        title=query.title,
        artist=query.artist,
        museum_name=query.museum_name,
        year_period=query.year_period,
        notes=query.notes,
        source="wikimedia",
        has_title_query=query.has_title_query,
        expected_medium_type=query.expected_medium_type,
        medium_type_filter=query.medium_type_filter,
        medium_hint=query.medium_hint,
    )


def _resolved_sources(query: ArtworkLookupQuery) -> list[str]:
    from app.sources.routing import resolve_lookup_sources

    return resolve_lookup_sources(query)
