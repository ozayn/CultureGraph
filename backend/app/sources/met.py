"""The Metropolitan Museum of Art open collection lookup (live API)."""

from __future__ import annotations

import logging
from typing import Any

import requests

from app.sources.base import ArtworkLookupCandidate, ArtworkLookupQuery
from app.sources.matching import api_search_query, resolve_search_terms, score_artwork_entry
from app.sources.museums import MET_SOURCE_NAME
from app.sources.routing import resolve_lookup_sources

logger = logging.getLogger(__name__)

MET_API_BASE = "https://collectionapi.metmuseum.org/public/collection/v1"
USER_AGENT = "CultureGraph/1.0 (+https://github.com/ozayn/CultureGraph)"
REQUEST_TIMEOUT = 12


def should_search_met(query: ArtworkLookupQuery) -> bool:
    return "met" in resolve_lookup_sources(query)


def collect_met_scored_candidates(
    query: ArtworkLookupQuery,
) -> list[tuple[float, dict, ArtworkLookupCandidate]]:
    if not should_search_met(query):
        return []

    search_text, artist_text = resolve_search_terms(query)
    if not search_text and not artist_text and not query.expanded_search_terms:
        return []

    search_query = api_search_query(query, search_text, artist_text)
    object_ids = _search_object_ids(search_query)
    if not object_ids:
        return []

    scored: list[tuple[float, dict, ArtworkLookupCandidate]] = []
    for object_id in object_ids[:8]:
        entry = _fetch_object(object_id)
        if not entry:
            continue
        if not entry.get("image_url"):
            continue

        score = score_artwork_entry(
            entry,
            search_text,
            artist_text,
            query.year_period,
            query=query,
            strict_artist_gate=not query.semantic_search,
        )
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
                    source_name=MET_SOURCE_NAME,
                    confidence=round(min(score, 0.95), 2),
                    rights_label=entry.get("rights_label"),
                    external_id=entry.get("object_id"),
                ),
            )
        )
    return scored


def search_met_collection(
    query: ArtworkLookupQuery,
    *,
    limit: int = 8,
) -> list[ArtworkLookupCandidate]:
    scored = collect_met_scored_candidates(query)
    scored.sort(key=lambda item: item[0], reverse=True)
    return [item[2] for item in scored[:limit]]


def _search_object_ids(query: str) -> list[str]:
    try:
        response = requests.get(
            f"{MET_API_BASE}/search",
            params={"q": query, "hasImages": "true"},
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        logger.warning("Met collection search failed: %s", exc)
        return []

    object_ids = payload.get("objectIDs") if isinstance(payload, dict) else None
    if not isinstance(object_ids, list):
        return []
    return [str(item) for item in object_ids if item]


def _fetch_object(object_id: str) -> dict[str, Any] | None:
    try:
        response = requests.get(
            f"{MET_API_BASE}/objects/{object_id}",
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        logger.warning("Met object fetch failed for %s: %s", object_id, exc)
        return None

    if not isinstance(payload, dict):
        return None

    title = (payload.get("title") or "").strip()
    if not title:
        return None

    primary_image = (payload.get("primaryImage") or "").strip()
    primary_thumb = (payload.get("primaryImageSmall") or primary_image).strip()
    rights = "Public Domain — The Met Open Access" if payload.get("isPublicDomain") else None

    return {
        "object_id": str(payload.get("objectID") or object_id),
        "title": title,
        "artist": (payload.get("artistDisplayName") or payload.get("culture") or "").strip() or None,
        "date": (payload.get("objectDate") or "").strip() or None,
        "medium": (payload.get("medium") or "").strip() or None,
        "image_url": primary_image or None,
        "image_thumbnail_url": primary_thumb or primary_image or None,
        "object_url": (payload.get("objectURL") or "").strip() or None,
        "accession_number": (payload.get("accessionNumber") or "").strip() or None,
        "rights_label": rights,
    }
