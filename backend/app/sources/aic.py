"""Art Institute of Chicago open collection lookup (live API)."""

from __future__ import annotations

import logging
from typing import Any

import requests

from app.sources.base import ArtworkLookupCandidate, ArtworkLookupQuery
from app.sources.matching import resolve_search_terms, score_artwork_entry
from app.sources.museums import AIC_SOURCE_NAME
from app.sources.routing import resolve_lookup_sources

logger = logging.getLogger(__name__)

AIC_API_BASE = "https://api.artic.edu/api/v1"
USER_AGENT = "CultureGraph/1.0 (+https://github.com/ozayn/CultureGraph)"
REQUEST_TIMEOUT = 12
AIC_FIELDS = (
    "id,title,artist_display,date_display,medium_display,image_id,"
    "is_public_domain,thumbnail,artwork_type_title"
)


def should_search_aic(query: ArtworkLookupQuery) -> bool:
    return "aic" in resolve_lookup_sources(query)


def collect_aic_scored_candidates(
    query: ArtworkLookupQuery,
) -> list[tuple[float, dict, ArtworkLookupCandidate]]:
    if not should_search_aic(query):
        return []

    search_text, artist_text = resolve_search_terms(query)
    if not search_text and not artist_text:
        return []

    search_query = " ".join(part for part in (search_text, artist_text) if part).strip()
    entries = _search_artworks(search_query)
    if not entries:
        return []

    scored: list[tuple[float, dict, ArtworkLookupCandidate]] = []
    for entry in entries:
        if not entry.get("image_url"):
            continue

        score = score_artwork_entry(entry, search_text, artist_text, query.year_period)
        if score < 0.15:
            continue

        scored.append(
            (
                score,
                entry,
                ArtworkLookupCandidate(
                    title=entry["title"],
                    artist=entry.get("artist"),
                    date=entry.get("date"),
                    medium=entry.get("medium"),
                    image_url=entry.get("image_url"),
                    image_thumbnail_url=entry.get("image_thumbnail_url"),
                    object_url=entry.get("object_url"),
                    accession_number=entry.get("accession_number"),
                    source_name=AIC_SOURCE_NAME,
                    confidence=round(min(score, 0.95), 2),
                    rights_label=entry.get("rights_label"),
                    external_id=entry.get("object_id"),
                ),
            )
        )
    return scored


def search_aic_collection(
    query: ArtworkLookupQuery,
    *,
    limit: int = 8,
) -> list[ArtworkLookupCandidate]:
    scored = collect_aic_scored_candidates(query)
    scored.sort(key=lambda item: item[0], reverse=True)
    return [item[2] for item in scored[:limit]]


def _search_artworks(query: str) -> list[dict[str, Any]]:
    try:
        response = requests.get(
            f"{AIC_API_BASE}/artworks/search",
            params={
                "q": query,
                "limit": 12,
                "fields": AIC_FIELDS,
            },
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        logger.warning("AIC collection search failed: %s", exc)
        return []

    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, list):
        return []

    entries: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        normalized = _normalize_aic_entry(item)
        if normalized:
            entries.append(normalized)
    return entries


def _normalize_aic_entry(item: dict[str, Any]) -> dict[str, Any] | None:
    title = (item.get("title") or "").strip()
    if not title:
        return None

    artwork_id = item.get("id")
    image_id = item.get("image_id")
    if not artwork_id or not image_id:
        return None

    thumb = None
    thumbnail = item.get("thumbnail")
    if isinstance(thumbnail, dict):
        thumb = (thumbnail.get("lqip") or thumbnail.get("alt_text") or "").strip() or None

    image_url = f"https://www.artic.edu/iiif/2/{image_id}/full/843,/0/default.jpg"
    image_thumbnail_url = (
        f"https://www.artic.edu/iiif/2/{image_id}/full/200,/0/default.jpg"
    )

    is_public = bool(item.get("is_public_domain"))
    rights = "Public Domain — Art Institute of Chicago" if is_public else None

    return {
        "object_id": str(artwork_id),
        "title": title,
        "artist": (item.get("artist_display") or "").strip() or None,
        "date": (item.get("date_display") or "").strip() or None,
        "medium": (item.get("medium_display") or "").strip() or None,
        "image_url": image_url,
        "image_thumbnail_url": image_thumbnail_url,
        "object_url": f"https://www.artic.edu/artworks/{artwork_id}",
        "accession_number": None,
        "rights_label": rights,
    }
