"""Provider selection and orchestration for web visual search."""

from __future__ import annotations

import logging

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
from app.services.web_visual_search.validation import public_url_host, verify_public_lens_image_url

logger = logging.getLogger(__name__)


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


def log_lens_search_attempt(
    *,
    provider_id: str,
    artwork: Artwork,
    image_url: str,
    has_crop: bool,
) -> None:
    logger.info(
        "lens search attempt provider=%s artwork_id=%s has_image_url=%s has_master_url=%s "
        "public_url_host=%s has_crop=%s",
        provider_id,
        artwork.id,
        bool((artwork.image_url or "").strip()),
        bool((artwork.image_master_url or "").strip()),
        public_url_host(image_url),
        has_crop,
    )


def search_artwork_with_lens(artwork: Artwork) -> LensSearchResult:
    provider = get_web_visual_search_provider()
    use_crop = provider.provider_id == PROVIDER_SEARCHAPI
    query = build_lens_search_query(artwork, use_crop=use_crop)
    log_lens_search_attempt(
        provider_id=provider.provider_id,
        artwork=artwork,
        image_url=query.image_url,
        has_crop=bool(query.crop),
    )
    verify_public_lens_image_url(query.image_url)
    return provider.search(artwork, query)
