"""Validate artwork images before calling web visual search providers."""

from __future__ import annotations

import ipaddress
import logging
from urllib.parse import urlparse

import requests

from app.services.web_visual_search.types import LensSearchError

logger = logging.getLogger(__name__)

_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "0.0.0.0"})


def public_url_host(url: str) -> str:
    return (urlparse(url).hostname or "").strip().lower()


def is_private_or_loopback_host(host: str) -> bool:
    normalized = host.strip().lower().rstrip(".")
    if not normalized:
        return True
    if normalized in _LOOPBACK_HOSTS:
        return True
    if normalized.endswith(".localhost"):
        return True
    try:
        address = ipaddress.ip_address(normalized)
    except ValueError:
        return False
    return address.is_private or address.is_loopback or address.is_link_local


def missing_public_api_base_url_message() -> str:
    return (
        "Web visual search needs PUBLIC_API_BASE_URL on the API server so uploaded "
        "/uploads/... photos resolve to a public HTTPS URL (for example "
        "https://your-api.up.railway.app). Alternatively, apply an https:// catalog "
        "image URL to the artwork."
    )


def missing_provider_api_key_message(provider_id: str) -> str:
    if provider_id == "searchapi":
        return (
            "Web visual search is not configured. Set SEARCHAPI_API_KEY on the API server "
            "when WEB_VISUAL_SEARCH_PROVIDER=searchapi."
        )
    return (
        "Web visual search is not configured. Set SERPAPI_API_KEY on the API server "
        "when WEB_VISUAL_SEARCH_PROVIDER=serpapi."
    )


def unauthorized_provider_message(provider_id: str) -> str:
    if provider_id == "searchapi":
        return (
            "Web visual search is not authorized. Check SEARCHAPI_API_KEY on the API server."
        )
    return (
        "Web visual search is not authorized. Check SERPAPI_API_KEY on the API server."
    )


def unreachable_image_message(*, host: str, status_code: int | None) -> str:
    status_hint = f"HTTP {status_code}" if status_code is not None else "could not be reached"
    return (
        f"The artwork image is not publicly reachable at {host} ({status_hint}). "
        "Uploaded photos must be served from PUBLIC_API_BASE_URL. "
        "If you develop locally, uploads usually exist only on this machine unless they are "
        "deployed to production or exposed through a public HTTPS tunnel (for example ngrok). "
        "Set PUBLIC_API_BASE_URL to the origin that actually serves the upload."
    )


def private_image_host_message(*, host: str) -> str:
    return (
        f"PUBLIC_API_BASE_URL resolves to a non-public host ({host}). "
        "Web visual search providers must download the image from the public internet. "
        "Use a public HTTPS API origin or tunnel and set PUBLIC_API_BASE_URL accordingly."
    )


def provider_validation_message(provider_error: str) -> str | None:
    lowered = provider_error.strip().lower()
    if lowered == "google lens didn't return any results.":
        return (
            "The provider could not search this image. Confirm PUBLIC_API_BASE_URL serves the "
            "artwork upload publicly over HTTPS and that the image URL opens in a browser."
        )
    return None


def verify_public_lens_image_url(image_url: str, *, timeout: float = 10.0) -> None:
    host = public_url_host(image_url)
    if not host:
        raise LensSearchError("Web visual search needs a valid public image URL.")

    if is_private_or_loopback_host(host):
        raise LensSearchError(private_image_host_message(host=host))

    try:
        response = requests.head(image_url, allow_redirects=True, timeout=timeout)
        if response.status_code == 405:
            response = requests.get(image_url, stream=True, allow_redirects=True, timeout=timeout)
            response.close()
    except requests.Timeout as exc:
        raise LensSearchError(
            f"The artwork image at {host} timed out while checking public reachability. "
            "Confirm PUBLIC_API_BASE_URL points to a reachable API origin."
        ) from exc
    except requests.RequestException as exc:
        raise LensSearchError(unreachable_image_message(host=host, status_code=None)) from exc

    if response.status_code >= 400:
        raise LensSearchError(
            unreachable_image_message(host=host, status_code=response.status_code)
        )

    content_type = (response.headers.get("content-type") or "").lower()
    if content_type.startswith("application/json"):
        raise LensSearchError(
            unreachable_image_message(host=host, status_code=response.status_code or 404)
        )
