"""HTTP helpers for web visual search providers."""

from __future__ import annotations

import logging
from typing import Any

import requests

from app.config import settings
from app.services.web_visual_search.redaction import redact_sensitive_text
from app.services.web_visual_search.types import LensSearchError, UNAUTHORIZED_LENS_MESSAGE

logger = logging.getLogger(__name__)


def request_status_code(exc: requests.RequestException) -> int | None:
    response = getattr(exc, "response", None)
    if response is not None:
        return getattr(response, "status_code", None)
    return None


def safe_request_error_message(exc: requests.RequestException) -> str:
    response = getattr(exc, "response", None)
    if response is not None:
        response_url = getattr(response, "url", None)
        if isinstance(response_url, str) and response_url:
            return redact_sensitive_text(f"HTTP {response.status_code} for {response_url}")
    return redact_sensitive_text(str(exc))


def is_authorization_failure(*, status_code: int | None, message: str) -> bool:
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


def log_lens_search_failure(
    *,
    provider_id: str,
    artwork_id: int,
    status_code: int | None,
    message: str,
) -> None:
    logger.warning(
        "lens search failed provider=%s artwork_id=%s status_code=%s error=%s",
        provider_id,
        artwork_id,
        status_code,
        redact_sensitive_text(message),
    )


def fetch_json(
    *,
    provider_id: str,
    artwork_id: int,
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=timeout or settings.serpapi_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.Timeout as exc:
        raise LensSearchError("Web visual search timed out. Try again in a moment.") from exc
    except requests.RequestException as exc:
        status_code = request_status_code(exc)
        safe_message = safe_request_error_message(exc)
        log_lens_search_failure(
            provider_id=provider_id,
            artwork_id=artwork_id,
            status_code=status_code,
            message=safe_message,
        )
        if is_authorization_failure(status_code=status_code, message=safe_message):
            raise LensSearchError(UNAUTHORIZED_LENS_MESSAGE) from exc
        raise LensSearchError("Web visual search request failed.") from exc
    except ValueError as exc:
        raise LensSearchError("Web visual search returned an invalid response.") from exc

    if not isinstance(payload, dict):
        raise LensSearchError("Web visual search returned an invalid response.")

    error_message = payload.get("error")
    if isinstance(error_message, str) and error_message.strip():
        safe_error = redact_sensitive_text(error_message.strip())
        if is_authorization_failure(status_code=None, message=safe_error):
            log_lens_search_failure(
                provider_id=provider_id,
                artwork_id=artwork_id,
                status_code=None,
                message=safe_error,
            )
            raise LensSearchError(UNAUTHORIZED_LENS_MESSAGE)
        raise LensSearchError(safe_error)

    return payload
