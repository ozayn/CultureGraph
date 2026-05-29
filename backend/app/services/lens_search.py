"""Optional web visual search fallback via SerpApi Google Lens."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests

from app.config import settings
from app.models import Artwork

logger = logging.getLogger(__name__)

WEB_VISUAL_SEARCH_SOURCE = "Web visual search"
SERPAPI_PROVIDER = "serpapi"
SERPAPI_SEARCH_URL = "https://serpapi.com/search.json"
REDACTED = "***REDACTED***"
SENSITIVE_QUERY_PARAMS = frozenset({"api_key", "key", "token"})
UNAUTHORIZED_LENS_MESSAGE = (
    "Web visual search is not authorized. Check SerpApi configuration."
)
_SENSITIVE_QUERY_PATTERN = re.compile(
    r"([?&](?:api_key|key|token)=)[^&\s]+",
    re.IGNORECASE,
)


class LensSearchError(RuntimeError):
    """Raised when web visual search cannot run."""


def redact_sensitive_url(url: str) -> str:
    if not url:
        return url
    try:
        parsed = urlparse(url)
        if not parsed.query:
            return url
        query = [
            (key, REDACTED if key.lower() in SENSITIVE_QUERY_PARAMS else value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        ]
        return urlunparse(parsed._replace(query=urlencode(query)))
    except Exception:
        return "<redacted-url>"


def redact_sensitive_text(text: str) -> str:
    if not text:
        return text
    redacted = _SENSITIVE_QUERY_PATTERN.sub(rf"\1{REDACTED}", text)
    if "://" in redacted:
        parts: list[str] = []
        last_end = 0
        for match in re.finditer(r"https?://[^\s\"']+", redacted):
            parts.append(redacted[last_end : match.start()])
            parts.append(redact_sensitive_url(match.group(0)))
            last_end = match.end()
        parts.append(redacted[last_end:])
        redacted = "".join(parts)
    return redacted


def _request_status_code(exc: requests.RequestException) -> int | None:
    response = getattr(exc, "response", None)
    if response is not None:
        return getattr(response, "status_code", None)
    return None


def _safe_request_error_message(exc: requests.RequestException) -> str:
    response = getattr(exc, "response", None)
    if response is not None:
        response_url = getattr(response, "url", None)
        if isinstance(response_url, str) and response_url:
            return redact_sensitive_text(f"HTTP {response.status_code} for {response_url}")
    return redact_sensitive_text(str(exc))


def _is_authorization_failure(*, status_code: int | None, message: str) -> bool:
    if status_code in {401, 403}:
        return True
    lowered = message.lower()
    return any(
        term in lowered
        for term in (
            "invalid api key",
            "api key",
            "unauthorized",
            "authentication",
            "forbidden",
        )
    )


def _log_lens_search_failure(
    *,
    artwork_id: int,
    status_code: int | None,
    message: str,
) -> None:
    logger.warning(
        "lens search failed provider=%s artwork_id=%s status_code=%s error=%s",
        SERPAPI_PROVIDER,
        artwork_id,
        status_code,
        redact_sensitive_text(message),
    )


def _raise_lens_request_error(
    exc: requests.RequestException,
    *,
    artwork_id: int,
) -> None:
    status_code = _request_status_code(exc)
    safe_message = _safe_request_error_message(exc)
    _log_lens_search_failure(
        artwork_id=artwork_id,
        status_code=status_code,
        message=safe_message,
    )
    if _is_authorization_failure(status_code=status_code, message=safe_message):
        raise LensSearchError(UNAUTHORIZED_LENS_MESSAGE) from exc
    raise LensSearchError("Web visual search request failed.") from exc


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


def resolve_lens_image_url(artwork: Artwork) -> str:
    image_url = (artwork.image_url or "").strip()
    if not image_url:
        raise LensSearchError("Upload a photo before running web visual search.")

    if image_url.startswith("http://") or image_url.startswith("https://"):
        return image_url

    if image_url.startswith("/uploads/"):
        base = (settings.public_api_base_url or "").strip().rstrip("/")
        if not base:
            raise LensSearchError(
                "Web visual search needs a publicly reachable image URL. "
                "Set PUBLIC_API_BASE_URL to your deployed API origin "
                "(for example https://your-api.up.railway.app), "
                "or apply a catalog image URL to the artwork first."
            )
        return f"{base}{image_url}"

    raise LensSearchError("Unsupported artwork image URL for web visual search.")


def _confidence_label_for_rank(rank: int) -> str:
    if rank <= 2:
        return "high"
    if rank <= 6:
        return "possible"
    return "weak"


def _candidate_key(item: dict[str, Any]) -> str:
    return "|".join(
        str(item.get(key) or "").strip()
        for key in ("link", "image", "thumbnail", "title", "source")
    )


def _parse_match_item(item: dict[str, Any], *, rank: int) -> LensSearchCandidate | None:
    title = str(item.get("title") or item.get("source") or "Web result").strip()
    if not title:
        title = "Web result"

    source = str(item.get("source") or WEB_VISUAL_SEARCH_SOURCE).strip() or WEB_VISUAL_SEARCH_SOURCE
    source_url = item.get("link")
    thumbnail_url = item.get("thumbnail")
    image_url = item.get("image") or thumbnail_url
    snippet = title if title != source else None

    if not any([source_url, thumbnail_url, image_url]):
        return None

    return LensSearchCandidate(
        title=title,
        source=source,
        source_url=str(source_url).strip() if source_url else None,
        thumbnail_url=str(thumbnail_url).strip() if thumbnail_url else None,
        image_url=str(image_url).strip() if image_url else None,
        snippet=snippet,
        source_rank=rank,
        confidence_label=_confidence_label_for_rank(rank),
    )


def _parse_candidates(payload: dict[str, Any], *, max_results: int) -> list[LensSearchCandidate]:
    matches: list[dict[str, Any]] = []
    for key in ("visual_matches", "exact_matches"):
        section = payload.get(key)
        if isinstance(section, list):
            matches.extend(item for item in section if isinstance(item, dict))

    candidates: list[LensSearchCandidate] = []
    seen: set[str] = set()
    rank = 0
    for item in matches:
        key = _candidate_key(item)
        if not key or key in seen:
            continue
        seen.add(key)
        rank += 1
        candidate = _parse_match_item(item, rank=rank)
        if candidate is None:
            continue
        candidates.append(candidate)
        if len(candidates) >= max_results:
            break
    return candidates


def search_artwork_with_lens(artwork: Artwork) -> LensSearchResult:
    api_key = (settings.serpapi_api_key or "").strip()
    if not api_key:
        raise LensSearchError(
            "Web visual search is not configured. Set SERPAPI_API_KEY on the API server."
        )

    query_image_url = resolve_lens_image_url(artwork)
    params = {
        "engine": "google_lens",
        "api_key": api_key,
        "url": query_image_url,
        "type": "all",
        "hl": "en",
    }

    try:
        response = requests.get(
            SERPAPI_SEARCH_URL,
            params=params,
            timeout=settings.serpapi_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.Timeout as exc:
        raise LensSearchError("Web visual search timed out. Try again in a moment.") from exc
    except requests.RequestException as exc:
        _raise_lens_request_error(exc, artwork_id=artwork.id)
    except ValueError as exc:
        raise LensSearchError("Web visual search returned an invalid response.") from exc

    if not isinstance(payload, dict):
        raise LensSearchError("Web visual search returned an invalid response.")

    error_message = payload.get("error")
    if isinstance(error_message, str) and error_message.strip():
        safe_error = redact_sensitive_text(error_message.strip())
        if _is_authorization_failure(status_code=None, message=safe_error):
            _log_lens_search_failure(
                artwork_id=artwork.id,
                status_code=None,
                message=safe_error,
            )
            raise LensSearchError(UNAUTHORIZED_LENS_MESSAGE)
        raise LensSearchError(safe_error)

    candidates = _parse_candidates(payload, max_results=max(1, settings.lens_search_max_results))
    notice = None
    if not candidates:
        notice = "No web visual matches were found for this image."

    logger.info(
        "lens search artwork_id=%s query=%s returned=%s",
        artwork.id,
        query_image_url,
        len(candidates),
    )

    return LensSearchResult(
        candidates=candidates,
        query_image_url=query_image_url,
        provider=WEB_VISUAL_SEARCH_SOURCE,
        notice=notice,
        disclaimer=(
            "Results come from optional third-party web visual search (SerpApi), "
            "not an official Google Lens API. Review each source before applying "
            "any image or metadata."
        ),
    )
