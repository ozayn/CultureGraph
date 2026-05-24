"""Tests for Claude JSON extraction helpers."""

import pytest

from app.services.claude_json import JsonExtractionError, extract_json_object, sanitize_response_preview


def test_extract_json_object_parses_raw_valid_json() -> None:
    payload = extract_json_object('{"visit": {"museum_name": "NGA"}, "entities": []}')
    assert payload["visit"]["museum_name"] == "NGA"


def test_extract_json_object_parses_fenced_json_block() -> None:
    text = """```json
{"entities": [{"name": "Test"}], "visit": {"summary": "ok"}}
```"""
    payload = extract_json_object(text)
    assert payload["entities"][0]["name"] == "Test"


def test_extract_json_object_parses_explanatory_text_around_json() -> None:
    text = """Here is the structured import draft you requested:

{"visit": {"museum_name": "Smithsonian"}, "entities": []}

Let me know if you need changes."""
    payload = extract_json_object(text)
    assert payload["visit"]["museum_name"] == "Smithsonian"


def test_extract_json_object_raises_on_invalid_response() -> None:
    with pytest.raises(JsonExtractionError):
        extract_json_object("This is not JSON at all.")


def test_sanitize_response_preview_truncates_long_text() -> None:
    preview = sanitize_response_preview("a" * 300, max_length=50)
    assert len(preview) <= 50
    assert preview.endswith("…")
