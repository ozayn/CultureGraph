"""Redact credentials from web visual search logs and errors."""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

REDACTED = "***REDACTED***"
SENSITIVE_QUERY_PARAMS = frozenset({"api_key", "key", "token"})
_SENSITIVE_QUERY_PATTERN = re.compile(
    r"([?&](?:api_key|key|token)=)[^&\s]+",
    re.IGNORECASE,
)
_BEARER_PATTERN = re.compile(r"(Bearer\s+)[^\s\"']+", re.IGNORECASE)


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
    redacted = _BEARER_PATTERN.sub(rf"\1{REDACTED}", redacted)
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
