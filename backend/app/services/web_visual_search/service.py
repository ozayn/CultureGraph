"""Provider selection and orchestration for web visual search."""

from __future__ import annotations

from app.config import settings
from app.models import Artwork
from app.services.web_visual_search.providers import SearchApiLensProvider, SerpApiLensProvider
from app.services.web_visual_search.query import build_lens_search_query
from app.services.web_visual_search.types import (
    PROVIDER_SEARCHAPI,
    PROVIDER_SERPAPI,
    LensSearchError,
    LensSearchResult,
    WebVisualSearchProvider,
)


def get_web_visual_search_provider() -> WebVisualSearchProvider:
    provider_name = (settings.web_visual_search_provider or PROVIDER_SERPAPI).strip().lower()
    if provider_name == PROVIDER_SERPAPI:
        return SerpApiLensProvider()
    if provider_name == PROVIDER_SEARCHAPI:
        return SearchApiLensProvider()
    raise LensSearchError(
        f"Unknown WEB_VISUAL_SEARCH_PROVIDER: {settings.web_visual_search_provider!r}. "
        f"Use {PROVIDER_SERPAPI!r} or {PROVIDER_SEARCHAPI!r}."
    )


def search_artwork_with_lens(artwork: Artwork) -> LensSearchResult:
    provider = get_web_visual_search_provider()
    use_crop = provider.provider_id == PROVIDER_SEARCHAPI
    query = build_lens_search_query(artwork, use_crop=use_crop)
    return provider.search(artwork, query)
