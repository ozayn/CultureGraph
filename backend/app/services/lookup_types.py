"""Shared types for museum artwork image lookup."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.sources.base import ArtworkLookupCandidate

LookupStrategy = Literal["exact", "fuzzy", "artist_fallback", "broad"]

STRATEGY_ORDER: tuple[LookupStrategy, ...] = (
    "exact",
    "fuzzy",
    "artist_fallback",
    "broad",
)


@dataclass(frozen=True)
class LookupResult:
    candidates: list[ArtworkLookupCandidate]
    query_strategy: LookupStrategy | None
    artist_fallback: bool = False
