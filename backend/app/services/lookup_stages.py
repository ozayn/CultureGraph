"""Multi-stage museum lookup: semantic → fuzzy → artist fallback → broad."""

from __future__ import annotations

from app.services.lookup_ranking import partition_lookup_candidates, rank_lookup_candidates
from app.services.lookup_types import SEMANTIC_STRATEGY_ORDER, STRATEGY_ORDER, LookupResult, LookupStrategy
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
    allow_wikimedia_fallback: bool = False,
) -> LookupResult:
    raw: list = []
    sources = _resolved_sources(query)
    if (
        allow_wikimedia_fallback
        and "wikimedia" not in sources
        and (query.source or "").strip().lower() == "all"
    ):
        sources = [*sources, "wikimedia"]
    if "nga" in sources:
        raw.extend(collect_nga_scored_candidates(query))
    if "smithsonian" in sources:
        raw.extend(collect_smithsonian_scored_candidates(query))
    if "met" in sources:
        raw.extend(collect_met_scored_candidates(query))
    if "aic" in sources:
        raw.extend(collect_aic_scored_candidates(query))
    if "wikimedia" in sources:
        raw.extend(collect_wikimedia_scored_candidates(query))

    candidate_limit = 36 if force_broad else (20 if query.semantic_search else (24 if len(sources) == 1 else 12))
    result = _rank_staged(
        raw,
        query,
        force_broad=force_broad,
        candidate_limit=candidate_limit,
    )
    if result.candidates or result.related_candidates:
        return result

    if allow_wikimedia_fallback and "wikimedia" not in sources:
        wiki_raw = collect_wikimedia_scored_candidates(_wikimedia_fallback_query(query))
        if wiki_raw:
            return _rank_staged(
                wiki_raw,
                query,
                force_broad=True,
                wikimedia_fallback=True,
                candidate_limit=candidate_limit,
            )

    return LookupResult(candidates=[], query_strategy=None)


def _rank_staged(
    raw: list,
    query: ArtworkLookupQuery,
    *,
    force_broad: bool = False,
    wikimedia_fallback: bool = False,
    candidate_limit: int = 12,
) -> LookupResult:
    if not raw:
        return LookupResult(candidates=[], query_strategy=None)

    strategies: tuple[LookupStrategy, ...]
    if query.semantic_search:
        strategies = SEMANTIC_STRATEGY_ORDER
    elif force_broad:
        strategies = ("broad",)
    else:
        strategies = STRATEGY_ORDER

    fallback_related: list = []
    fallback_strategy: LookupStrategy | None = None
    fallback_artist = False

    for strategy in strategies:
        ranked = rank_lookup_candidates(
            raw,
            query,
            strategy=strategy,
            limit=candidate_limit,
        )
        if not ranked:
            continue

        primary, related = partition_lookup_candidates(ranked)
        artist_fallback = strategy in {"artist_fallback", "broad"} or wikimedia_fallback

        if primary:
            return LookupResult(
                candidates=primary,
                related_candidates=related,
                query_strategy=strategy,
                artist_fallback=artist_fallback,
            )

        if related and not fallback_related:
            fallback_related = related
            fallback_strategy = strategy
            fallback_artist = artist_fallback

    if fallback_related:
        return LookupResult(
            candidates=[],
            related_candidates=fallback_related,
            query_strategy=fallback_strategy,
            artist_fallback=fallback_artist,
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
        semantic_search=query.semantic_search,
        expanded_search_terms=query.expanded_search_terms,
    )


def _resolved_sources(query: ArtworkLookupQuery) -> list[str]:
    from app.sources.routing import resolve_lookup_sources

    return resolve_lookup_sources(query)
