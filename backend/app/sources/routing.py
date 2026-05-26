"""Decide which museum lookup adapters to query for a given artwork."""

from __future__ import annotations

from app.sources.base import ArtworkLookupQuery
from app.sources.museums import (
    NGA_SOURCE_NAME,
    SMITHSONIAN_EXPLICIT_SOURCES,
    SMITHSONIAN_SOURCE_NAME,
    is_nga_museum,
    is_smithsonian_museum,
)


def resolve_lookup_sources(query: ArtworkLookupQuery) -> list[str]:
    if query.source:
        normalized = query.source.strip().lower()
        if normalized == "all":
            return ["nga", "smithsonian"]
        if normalized in {"nga", "national gallery of art"}:
            return ["nga"]
        if normalized in SMITHSONIAN_EXPLICIT_SOURCES:
            return ["smithsonian"]
        return []

    if is_nga_museum(query.museum_name):
        return ["nga"]
    if is_smithsonian_museum(query.museum_name):
        return ["smithsonian"]
    if query.museum_name:
        return []
    return ["nga", "smithsonian"]


def sources_searched_labels(query: ArtworkLookupQuery) -> list[str]:
    keys = resolve_lookup_sources(query)
    labels: list[str] = []
    if "nga" in keys:
        labels.append(NGA_SOURCE_NAME)
    if "smithsonian" in keys:
        labels.append(SMITHSONIAN_SOURCE_NAME)
    return labels
