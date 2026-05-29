"""SearchAPI.io Google Lens web visual search provider."""

from __future__ import annotations

import logging

from app.config import settings
from app.models import Artwork
from app.services.web_visual_search.http import fetch_json
from app.services.web_visual_search.parsing import parse_lens_candidates
from app.services.web_visual_search.types import (
    PROVIDER_DISPLAY_NAMES,
    PROVIDER_SEARCHAPI,
    LensSearchError,
    LensSearchQuery,
    LensSearchResult,
)
from app.services.web_visual_search.validation import missing_provider_api_key_message

logger = logging.getLogger(__name__)

SEARCHAPI_SEARCH_URL = "https://www.searchapi.io/api/v1/search"


class SearchApiLensProvider:
    provider_id = PROVIDER_SEARCHAPI
    display_name = PROVIDER_DISPLAY_NAMES[PROVIDER_SEARCHAPI]

    def search(self, artwork: Artwork, query: LensSearchQuery) -> LensSearchResult:
        api_key = (settings.searchapi_api_key or "").strip()
        if not api_key:
            raise LensSearchError(missing_provider_api_key_message(self.provider_id))

        params: dict[str, str] = {
            "engine": "google_lens",
            "api_key": api_key,
            "url": query.image_url,
        }
        if query.crop:
            params["crop"] = query.crop

        payload = fetch_json(
            provider_id=self.provider_id,
            artwork_id=artwork.id,
            url=SEARCHAPI_SEARCH_URL,
            params=params,
        )
        candidates = parse_lens_candidates(
            payload,
            max_results=max(1, settings.lens_search_max_results),
        )
        notice = None
        if not candidates:
            notice = "No web visual matches were found for this image."

        logger.info(
            "lens search provider=%s artwork_id=%s query=%s crop=%s returned=%s",
            self.provider_id,
            artwork.id,
            query.image_url,
            bool(query.crop),
            len(candidates),
        )

        return LensSearchResult(
            candidates=candidates,
            query_image_url=query.image_url,
            provider=self.display_name,
            notice=notice,
            disclaimer=(
                "Results come from optional third-party web visual search (SearchAPI), "
                "not an official Google Lens API. Review each source before applying "
                "any image or metadata."
            ),
        )
