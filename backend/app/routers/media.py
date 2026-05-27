"""Proxy museum thumbnail URLs for reliable card rendering."""

from __future__ import annotations

import logging
from urllib.parse import urlparse

import requests
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

logger = logging.getLogger(__name__)

router = APIRouter(tags=["media"])

ALLOWED_IMAGE_HOST_SUFFIXES = (
    "nga.gov",
    "si.edu",
    "smithsonian.edu",
    "americanart.si.edu",
    "metmuseum.org",
    "images.metmuseum.org",
    "artic.edu",
    "www.artic.edu",
    "upload.wikimedia.org",
    "commons.wikimedia.org",
)

USER_AGENT = "CultureGraph/1.0 (+https://github.com/ozayn/CultureGraph)"


def _host_allowed(hostname: str | None) -> bool:
    if not hostname:
        return False
    host = hostname.lower()
    return any(host == suffix or host.endswith(f".{suffix}") for suffix in ALLOWED_IMAGE_HOST_SUFFIXES)


@router.get("/image-proxy")
def image_proxy(url: str = Query(..., max_length=2048)) -> Response:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise HTTPException(status_code=400, detail="Only https image URLs are supported.")
    if not _host_allowed(parsed.hostname):
        raise HTTPException(status_code=403, detail="Image host is not allowed.")

    try:
        upstream = requests.get(
            url,
            timeout=20,
            headers={"User-Agent": USER_AGENT, "Accept": "image/*"},
        )
    except requests.RequestException as exc:
        logger.warning("image-proxy fetch failed for %s: %s", url, exc)
        raise HTTPException(status_code=502, detail="Could not fetch image.") from exc

    if upstream.status_code >= 400:
        raise HTTPException(
            status_code=upstream.status_code,
            detail="Upstream image is unavailable.",
        )

    content_type = upstream.headers.get("content-type", "image/jpeg")
    if not content_type.startswith("image/"):
        content_type = "image/jpeg"

    return Response(
        content=upstream.content,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )
