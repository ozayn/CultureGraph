"""Optional web visual search fallback via SerpApi Google Lens."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import requests

from app.config import settings
from app.models import Artwork

logger = logging.getLogger(__name__)

WEB_VISUAL_SEARCH_SOURCE = "Web visual search"
SERPAPI_SEARCH_URL = "https://serpapi.com/search.json"


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
        logger.warning("SerpApi lens search failed artwork_id=%s error=%s", artwork.id, exc)
        raise LensSearchError("Web visual search request failed.") from exc
    except ValueError as exc:
        raise LensSearchError("Web visual search returned an invalid response.") from exc

    if not isinstance(payload, dict):
        raise LensSearchError("Web visual search returned an invalid response.")

    error_message = payload.get("error")
    if isinstance(error_message, str) and error_message.strip():
        raise LensSearchError(error_message.strip())

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
