"""Build API responses for museum artwork lookup."""

from __future__ import annotations

from app.schemas import ArtworkLookupCandidateRead, ArtworkLookupResponse
from app.services.lookup_types import LookupResult
from app.sources.base import ArtworkLookupQuery
from app.sources.routing import sources_searched_labels


def lookup_notice(
    *,
    lookup_result: LookupResult,
    query: ArtworkLookupQuery,
    query_used: str,
    visual_keywords: bool = False,
) -> str | None:
    if visual_keywords:
        return "Searched museum collections using visual style and subject keywords."

    if lookup_result.candidates:
        if lookup_result.artist_fallback:
            artist_label = (query.artist or "").strip() or "this artist"
            return f"No exact title match found. Showing related works by {artist_label}."
        return None

    if lookup_result.related_candidates and not lookup_result.candidates:
        return (
            "No close official match found. "
            "Review weak related results below, or try a manual title/artist search."
        )

    if not query_used.strip():
        return "Add a title or artist to improve collection matching."

    searched = ", ".join(sources_searched_labels(query)) or "open collections"
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
) -> ArtworkLookupResponse:
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
        notice=lookup_notice(
            lookup_result=lookup_result,
            query=query,
            query_used=query_used,
            visual_keywords=visual_keywords,
        ),
    )
