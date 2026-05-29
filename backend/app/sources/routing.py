"""Decide which museum lookup adapters to query for a given artwork."""

from __future__ import annotations

from app.sources.base import ArtworkLookupQuery
from app.sources.museums import (
    AIC_SOURCE_NAME,
    MET_SOURCE_NAME,
    NGA_SOURCE_NAME,
    SMITHSONIAN_EXPLICIT_SOURCES,
    SMITHSONIAN_SOURCE_NAME,
    WIKIMEDIA_SOURCE_NAME,
    is_aic_museum,
    is_met_museum,
    is_nga_museum,
    is_smithsonian_museum,
)

MUSEUM_SOURCES = ("nga", "smithsonian", "met", "aic")
ALL_OPEN_SOURCES = (*MUSEUM_SOURCES, "wikimedia")

MUSEUM_SHORT_LABELS: dict[str, str] = {
    NGA_SOURCE_NAME: "NGA",
    SMITHSONIAN_SOURCE_NAME: "Smithsonian",
    MET_SOURCE_NAME: "Met",
    AIC_SOURCE_NAME: "Art Institute of Chicago",
}


def is_recognized_museum(museum_name: str | None) -> bool:
    return bool(
        is_nga_museum(museum_name)
        or is_smithsonian_museum(museum_name)
        or is_met_museum(museum_name)
        or is_aic_museum(museum_name)
    )


def museum_collection_display_name(museum_name: str | None) -> str | None:
    if is_nga_museum(museum_name):
        return NGA_SOURCE_NAME
    if is_smithsonian_museum(museum_name):
        return SMITHSONIAN_SOURCE_NAME
    if is_met_museum(museum_name):
        return MET_SOURCE_NAME
    if is_aic_museum(museum_name):
        return AIC_SOURCE_NAME
    return None


def museum_short_label(collection_name: str | None) -> str | None:
    if not collection_name:
        return None
    return MUSEUM_SHORT_LABELS.get(collection_name, collection_name)


def resolve_broaden_sources(*, include_wikimedia: bool = True) -> list[str]:
    keys = list(MUSEUM_SOURCES)
    if include_wikimedia:
        keys.append("wikimedia")
    return keys


def resolve_lookup_sources(query: ArtworkLookupQuery) -> list[str]:
    if query.source:
        normalized = query.source.strip().lower()
        if normalized == "all":
            return list(MUSEUM_SOURCES)
        if normalized in {"nga", "national gallery of art"}:
            return ["nga"]
        if normalized in SMITHSONIAN_EXPLICIT_SOURCES:
            return ["smithsonian"]
        if normalized in {"met", "the met", "metropolitan museum of art"}:
            return ["met"]
        if normalized in {"aic", "art institute of chicago", "artic"}:
            return ["aic"]
        if normalized in {"wikimedia", "commons", "wikipedia"}:
            return ["wikimedia"]
        return []

    if is_nga_museum(query.museum_name):
        return ["nga"]
    if is_smithsonian_museum(query.museum_name):
        return ["smithsonian"]
    if is_met_museum(query.museum_name):
        return ["met"]
    if is_aic_museum(query.museum_name):
        return ["aic"]
    return []


def sources_searched_labels(query: ArtworkLookupQuery) -> list[str]:
    keys = resolve_lookup_sources(query)
    labels: list[str] = []
    if "nga" in keys:
        labels.append(NGA_SOURCE_NAME)
    if "smithsonian" in keys:
        labels.append(SMITHSONIAN_SOURCE_NAME)
    if "met" in keys:
        labels.append(MET_SOURCE_NAME)
    if "aic" in keys:
        labels.append(AIC_SOURCE_NAME)
    if "wikimedia" in keys:
        labels.append(WIKIMEDIA_SOURCE_NAME)
    return labels
