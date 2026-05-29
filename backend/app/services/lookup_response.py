"""Build API responses for museum artwork lookup."""

from __future__ import annotations

from app.schemas import ArtworkLookupCandidateRead, ArtworkLookupResponse
from app.services.lookup_types import LookupResult
from app.sources.base import ArtworkLookupQuery
from app.sources.routing import (
    museum_collection_display_name,
    museum_short_label,
    resolve_lookup_sources,
    sources_searched_labels,
)


def lookup_search_scope(
    *,
    query: ArtworkLookupQuery,
    broaden_search: bool = False,
) -> str:
    if broaden_search or (query.source or "").strip().lower() == "all":
        return "broad"
    if resolve_lookup_sources(query):
        return "museum"
    return "none"


def lookup_notice(
    *,
    lookup_result: LookupResult,
    query: ArtworkLookupQuery,
    query_used: str,
    visual_keywords: bool = False,
    search_scope: str = "museum",
    museum_collection_name: str | None = None,
) -> str | None:
    collection_label = museum_collection_name or (
        sources_searched_labels(query)[0] if sources_searched_labels(query) else None
    )
    short_label = museum_short_label(collection_label) if collection_label else None

    if visual_keywords and collection_label:
        return f"Searched {collection_label} using visual style and subject keywords."

    if visual_keywords:
        return "Searched museum collections using visual style and subject keywords."

    if lookup_result.candidates:
        if lookup_result.artist_fallback:
            artist_label = (query.artist or "").strip() or "this artist"
            if collection_label:
                return (
                    f"No close match in {collection_label}. "
                    f"Showing related works by {artist_label}."
                )
            return f"No close match found. Showing related works by {artist_label}."
        return None

    if lookup_result.related_candidates and not lookup_result.candidates:
        if short_label:
            return (
                f"No close match in {collection_label}. "
                f"Review possible {short_label} candidates below, or try a manual title/artist search."
            )
        return (
            "No close official match found. "
            "Review weak related results below, or try a manual title/artist search."
        )

    if not query_used.strip():
        if collection_label:
            return f"Add a title or artist to search the {collection_label} collection."
        return "Add a title or artist to improve collection matching."

    if search_scope == "broad":
        searched = ", ".join(sources_searched_labels(query)) or "open collections"
        return f"No close official match found in {searched}."

    if collection_label:
        return f"No close official match found in the {collection_label} collection."

    searched = ", ".join(sources_searched_labels(query)) or "the selected collections"
    return f"No close official match found in {searched}."


def lookup_response_from_result(
    lookup_result: LookupResult,
    *,
    query: ArtworkLookupQuery,
    query_used: str,
    query_source: str,
    alternate_title: str | None = None,
    expected_medium_type: str | None = None,
    medium_type_filter: str = "any",
    visual_keywords: bool = False,
    search_scope: str | None = None,
    visit_museum_name: str | None = None,
    broaden_search: bool = False,
    retrieval_intent: str = "standard",
) -> ArtworkLookupResponse:
    resolved_scope = search_scope or lookup_search_scope(
        query=query,
        broaden_search=broaden_search,
    )
    museum_collection_name = museum_collection_display_name(visit_museum_name)
    if resolved_scope == "broad":
        museum_collection_name = None

    return ArtworkLookupResponse(
        candidates=[
            ArtworkLookupCandidateRead.model_validate(item, from_attributes=True)
            for item in lookup_result.candidates
        ],
        related_candidates=[
            ArtworkLookupCandidateRead.model_validate(item, from_attributes=True)
            for item in lookup_result.related_candidates
        ],
        sources_searched=sources_searched_labels(query),
        query_used=query_used,
        query_source=query_source,  # type: ignore[arg-type]
        query_strategy=lookup_result.query_strategy,
        artist_fallback=lookup_result.artist_fallback,
        alternate_title=alternate_title,
        expected_medium_type=expected_medium_type,
        medium_type_filter=medium_type_filter,
        search_scope=resolved_scope,  # type: ignore[arg-type]
        museum_collection_name=museum_collection_name,
        retrieval_intent=retrieval_intent,  # type: ignore[arg-type]
        notice=lookup_notice(
            lookup_result=lookup_result,
            query=query,
            query_used=query_used,
            visual_keywords=visual_keywords,
            search_scope=resolved_scope,
            museum_collection_name=museum_collection_name,
        ),
    )
