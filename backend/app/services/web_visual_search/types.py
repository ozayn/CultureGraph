"""Shared types for web visual search providers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models import Artwork

WEB_VISUAL_SEARCH_SOURCE = "Web visual search"
PROVIDER_SERPAPI = "serpapi"
PROVIDER_SEARCHAPI = "searchapi"

PROVIDER_DISPLAY_NAMES = {
    PROVIDER_SERPAPI: "Web visual search (SerpApi)",
    PROVIDER_SEARCHAPI: "Web visual search (SearchAPI)",
}

UNAUTHORIZED_LENS_MESSAGE = (
    "Web visual search is not authorized. Check web visual search provider configuration."
)


class LensSearchError(RuntimeError):
    """Raised when web visual search cannot run."""


@dataclass(frozen=True)
class LensSearchCandidate:
    title: str
    source: str
    source_url: str | None
    thumbnail_url: str | None
    image_url: str | None
    snippet: str | None
    source_rank: int
    confidence_label: str


@dataclass(frozen=True)
class LensSearchResult:
    candidates: list[LensSearchCandidate]
    query_image_url: str | None
    provider: str
    notice: str | None
    disclaimer: str


@dataclass(frozen=True)
class LensSearchQuery:
    image_url: str
    crop: str | None = None


class WebVisualSearchProvider(Protocol):
    provider_id: str
    display_name: str

    def search(self, artwork: Artwork, query: LensSearchQuery) -> LensSearchResult: ...
