"""Robust JSON extraction from Claude text responses."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class JsonExtractionError(ValueError):
    """Raised when Claude text cannot be parsed as a JSON object."""


def sanitize_response_preview(text: str, *, max_length: int = 240) -> str:
    collapsed = re.sub(r"\s+", " ", text.strip())
    if len(collapsed) <= max_length:
        return collapsed
    return f"{collapsed[: max_length - 1]}…"


def _strip_markdown_fences(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped

    stripped = re.sub(r"^```(?:json|JSON)?\s*", "", stripped)
    stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def _find_first_json_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None

    depth = 0
    in_string = False
    escape = False

    for index in range(start, len(text)):
        char = text[index]

        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue

        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]

    return None


def extract_json_object(text: str) -> dict[str, Any]:
    if not text or not text.strip():
        raise JsonExtractionError("Claude returned an empty response.")

    candidates: list[str] = []
    stripped = text.strip()
    candidates.append(stripped)
    candidates.append(_strip_markdown_fences(stripped))

    embedded = _find_first_json_object(stripped)
    if embedded:
        candidates.append(embedded)
        candidates.append(_strip_markdown_fences(embedded))

    seen: set[str] = set()
    last_error: json.JSONDecodeError | None = None

    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = exc
            continue

        if not isinstance(payload, dict):
            raise JsonExtractionError("Claude JSON response must be a single object.")
        return payload

    preview = sanitize_response_preview(text)
    logger.warning("Claude JSON parse failed. Response preview: %s", preview)
    detail = "Claude returned a response that could not be parsed as JSON."
    if last_error is not None:
        detail = f"{detail} ({last_error.msg})"
    raise JsonExtractionError(detail)


def extract_json_object_lenient(text: str) -> dict[str, Any] | None:
    try:
        return extract_json_object(text)
    except JsonExtractionError:
        return None
