"""Provider-based web visual search."""

from app.services.web_visual_search.crop import build_normalized_crop_parameter
from app.services.web_visual_search.parsing import parse_lens_candidates
from app.services.web_visual_search.query import build_lens_search_query, resolve_lens_image_url
from app.services.web_visual_search.redaction import redact_sensitive_text, redact_sensitive_url
from app.services.web_visual_search.service import get_web_visual_search_provider, search_artwork_with_lens
from app.services.web_visual_search.types import (
    PROVIDER_DISPLAY_NAMES,
    PROVIDER_SEARCHAPI,
    PROVIDER_SERPAPI,
    UNAUTHORIZED_LENS_MESSAGE,
    WEB_VISUAL_SEARCH_SOURCE,
    LensSearchCandidate,
    LensSearchError,
    LensSearchQuery,
    LensSearchResult,
    WebVisualSearchProvider,
    unauthorized_lens_message,
)
from app.services.web_visual_search.validation import (
    missing_provider_api_key_message,
    missing_public_api_base_url_message,
    verify_public_lens_image_url,
)

__all__ = [
    "PROVIDER_DISPLAY_NAMES",
    "PROVIDER_SEARCHAPI",
    "PROVIDER_SERPAPI",
    "UNAUTHORIZED_LENS_MESSAGE",
    "WEB_VISUAL_SEARCH_SOURCE",
    "LensSearchCandidate",
    "LensSearchError",
    "LensSearchQuery",
    "LensSearchResult",
    "WebVisualSearchProvider",
    "build_lens_search_query",
    "build_normalized_crop_parameter",
    "get_web_visual_search_provider",
    "parse_lens_candidates",
    "redact_sensitive_text",
    "redact_sensitive_url",
    "resolve_lens_image_url",
    "search_artwork_with_lens",
    "unauthorized_lens_message",
    "missing_provider_api_key_message",
    "missing_public_api_base_url_message",
    "verify_public_lens_image_url",
]
