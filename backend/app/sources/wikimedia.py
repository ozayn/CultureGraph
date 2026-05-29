"""Wikimedia Commons lookup fallback for artwork identification."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

import requests

from app.sources.base import ArtworkLookupCandidate, ArtworkLookupQuery
from app.sources.matching import api_search_query, resolve_search_terms, score_artwork_entry
from app.sources.museums import WIKIMEDIA_SOURCE_NAME
from app.sources.routing import resolve_lookup_sources

logger = logging.getLogger(__name__)

WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "CultureGraph/1.0 (+https://github.com/ozayn/CultureGraph)"
REQUEST_TIMEOUT = 12


def should_search_wikimedia(query: ArtworkLookupQuery) -> bool:
    return "wikimedia" in resolve_lookup_sources(query)


def collect_wikimedia_scored_candidates(
    query: ArtworkLookupQuery,
) -> list[tuple[float, dict, ArtworkLookupCandidate]]:
    if not should_search_wikimedia(query):
        return []

    search_text, artist_text = resolve_search_terms(query)
    if not search_text and not artist_text and not query.expanded_search_terms:
        return []

    search_query = api_search_query(query, search_text, artist_text, suffix="painting")
    entries = _search_commons(search_query)
    if not entries:
        return []

    scored: list[tuple[float, dict, ArtworkLookupCandidate]] = []
    for entry in entries:
        score = score_artwork_entry(
            entry,
            search_text,
            artist_text,
            query.year_period,
            query=query,
            strict_artist_gate=not query.semantic_search,
        )
        if score < 0.12:
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
                    accession_number=None,
                    source_name=WIKIMEDIA_SOURCE_NAME,
                    confidence=round(min(score * 0.85, 0.88), 2),
                    rights_label=entry.get("rights_label"),
                    external_id=entry.get("object_id"),
                ),
            )
        )
    return scored


def search_wikimedia_collection(
    query: ArtworkLookupQuery,
    *,
    limit: int = 8,
) -> list[ArtworkLookupCandidate]:
    scored = collect_wikimedia_scored_candidates(query)
    scored.sort(key=lambda item: item[0], reverse=True)
    return [item[2] for item in scored[:limit]]


def _search_commons(query: str) -> list[dict[str, Any]]:
    try:
        response = requests.get(
            WIKIMEDIA_API,
            params={
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrsearch": query,
                "gsrlimit": 10,
                "gsrnamespace": 6,
                "prop": "imageinfo|info",
                "inprop": "url",
                "iiprop": "url|thumburl|extmetadata|mime",
                "iiurlwidth": 400,
            },
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        logger.warning("Wikimedia Commons search failed: %s", exc)
        return []

    pages = payload.get("query", {}).get("pages", {}) if isinstance(payload, dict) else {}
    if not isinstance(pages, dict):
        return []

    entries: list[dict[str, Any]] = []
    for page in pages.values():
        if not isinstance(page, dict):
            continue
        normalized = _normalize_commons_page(page)
        if normalized:
            entries.append(normalized)
    return entries


def _normalize_commons_page(page: dict[str, Any]) -> dict[str, Any] | None:
    imageinfo = page.get("imageinfo")
    if not isinstance(imageinfo, list) or not imageinfo:
        return None

    info = imageinfo[0]
    if not isinstance(info, dict):
        return None

    mime = (info.get("mime") or "").lower()
    if mime and not mime.startswith("image/"):
        return None

    image_url = (info.get("url") or "").strip()
    if not image_url:
        return None

    thumb_url = (info.get("thumburl") or image_url).strip()
    title = _humanize_commons_title(page.get("title") or "")
    if not title:
        return None

    page_url = (page.get("canonicalurl") or info.get("descriptionurl") or "").strip()
    if not page_url and page.get("title"):
        page_url = f"https://commons.wikimedia.org/wiki/{quote(str(page['title']).replace(' ', '_'))}"

    artist = None
    date = None
    rights = "Wikimedia Commons — verify license on source page"
    extmetadata = info.get("extmetadata")
    if isinstance(extmetadata, dict):
        artist = _metadata_value(extmetadata, "Artist")
        date = _metadata_value(extmetadata, "DateTimeOriginal") or _metadata_value(
            extmetadata, "DateTime"
        )
        license_short = _metadata_value(extmetadata, "LicenseShortName")
        if license_short:
            rights = f"Wikimedia Commons — {license_short}"

    return {
        "object_id": str(page.get("pageid") or title),
        "title": title,
        "artist": artist,
        "date": date,
        "medium": None,
        "image_url": image_url,
        "image_thumbnail_url": thumb_url,
        "object_url": page_url or None,
        "rights_label": rights,
    }


def _humanize_commons_title(raw: str) -> str:
    title = raw.strip()
    if title.lower().startswith("file:"):
        title = title[5:]
    title = title.rsplit(".", 1)[0]
    return title.replace("_", " ").strip()


def _metadata_value(extmetadata: dict[str, Any], key: str) -> str | None:
    item = extmetadata.get(key)
    if not isinstance(item, dict):
        return None
    value = (item.get("value") or "").strip()
    return value or None
