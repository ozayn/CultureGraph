from datetime import date
from types import SimpleNamespace

import pytest

from app.config import settings
from app.schemas import MuseumNotesImportRequest
from app.services.museum_notes_import import (
    ClaudeMuseumNotesImportProvider,
    IMPORT_FALLBACK_WARNING,
    IMPORT_SCHEMA_MISMATCH_MESSAGE,
    IMPORT_TIMEOUT_WARNING,
    IMPORT_TOOL_NAME,
    _parse_claude_import_payload,
    _read_claude_import_payload,
)
from app.services.research import ResearchProviderError
from anthropic import APITimeoutError


def test_read_claude_import_payload_from_tool_use() -> None:
    message = SimpleNamespace(
        content=[
            SimpleNamespace(
                type="tool_use",
                name=IMPORT_TOOL_NAME,
                input={
                    "visit": {
                        "museum_name": "NGA",
                        "city": "Washington, DC",
                        "visit_date": "2026-05-24",
                        "summary": "Visit summary",
                    },
                    "entities": [
                        {
                            "entity_type": "artist",
                            "name": "Thomas Moran",
                        }
                    ],
                },
            )
        ]
    )
    payload = _read_claude_import_payload(message)
    assert payload["visit"]["museum_name"] == "NGA"
    assert payload["entities"][0]["name"] == "Thomas Moran"


def test_parse_claude_import_payload_normalizes_legacy_artworks() -> None:
    request = MuseumNotesImportRequest(
        text="Thomas Moran",
        default_museum="Smithsonian American Art Museum",
        default_city="Washington, DC",
    )
    parsed = _parse_claude_import_payload(
        {
            "visit": {
                "museum_name": "Smithsonian American Art Museum",
                "city": "Washington, DC",
                "visit_date": "2026-05-24",
                "summary": "Summary",
            },
            "artworks": [
                {
                    "artist": "Thomas Moran",
                    "notes": "Western landscape",
                }
            ],
        },
        request,
    )
    assert parsed.entities[0].entity_type.value == "artwork"
    assert parsed.entities[0].artist == "Thomas Moran"


def test_read_claude_import_payload_from_fenced_text() -> None:
    message = SimpleNamespace(
        content=[
            SimpleNamespace(
                type="text",
                text='```json\n{"visit": {"museum_name": "NGA", "city": "DC", "visit_date": "2026-05-24", "summary": "s"}, "entities": [], "concept_links": []}\n```',
            )
        ]
    )
    payload = _read_claude_import_payload(message)
    assert payload["visit"]["city"] == "DC"


@pytest.mark.asyncio
async def test_claude_import_falls_back_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "app_env", "production")

    provider = ClaudeMuseumNotesImportProvider("test-api-key")

    async def fake_create(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text="Sorry, I cannot produce JSON right now.")]
        )

    provider._client = SimpleNamespace(messages=SimpleNamespace(create=fake_create))

    request = MuseumNotesImportRequest(
        text="Thomas Moran and Manifest Destiny — dramatic western landscape",
        default_museum="Smithsonian American Art Museum",
        default_city="Washington, DC",
        visit_date=date(2026, 5, 24),
    )

    result = await provider.extract(request)

    assert result.source == "mock"
    assert result.ai_warning == IMPORT_FALLBACK_WARNING
    assert result.entities


@pytest.mark.asyncio
async def test_claude_import_raises_helpful_error_in_development(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_env", "development")

    provider = ClaudeMuseumNotesImportProvider("test-api-key")

    async def fake_create(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(
            content=[
                SimpleNamespace(
                    type="tool_use",
                    name=IMPORT_TOOL_NAME,
                    input={"visit": {"museum_name": "NGA"}, "entities": "not-an-array"},
                )
            ]
        )

    provider._client = SimpleNamespace(messages=SimpleNamespace(create=fake_create))

    request = MuseumNotesImportRequest(
        text="Thomas Moran and Manifest Destiny",
        default_museum="Smithsonian American Art Museum",
        default_city="Washington, DC",
    )

    with pytest.raises(ResearchProviderError, match=IMPORT_SCHEMA_MISMATCH_MESSAGE):
        await provider.extract(request)


@pytest.mark.asyncio
async def test_claude_import_validation_error_falls_back_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_env", "production")

    provider = ClaudeMuseumNotesImportProvider("test-api-key")

    async def fake_create(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(
            content=[
                SimpleNamespace(
                    type="tool_use",
                    name=IMPORT_TOOL_NAME,
                    input={"visit": {"museum_name": "NGA"}, "entities": "not-an-array"},
                )
            ]
        )

    provider._client = SimpleNamespace(messages=SimpleNamespace(create=fake_create))

    request = MuseumNotesImportRequest(
        text="Sam Gilliam — draped canvas",
        default_museum="Smithsonian American Art Museum",
        default_city="Washington, DC",
    )

    result = await provider.extract(request)
    assert result.ai_warning == IMPORT_FALLBACK_WARNING
    assert result.source == "mock"


@pytest.mark.asyncio
async def test_claude_import_accepts_current_entities_tool_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_env", "development")

    provider = ClaudeMuseumNotesImportProvider("test-api-key")

    async def fake_create(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(
            content=[
                SimpleNamespace(
                    type="tool_use",
                    name=IMPORT_TOOL_NAME,
                    input={
                        "visit": {
                            "museum_name": "National Gallery of Art",
                            "city": "Washington, DC",
                            "visit_date": "2026-05-24",
                            "summary": "NGA visit notes",
                        },
                        "entities": [
                            {
                                "entity_type": "artist",
                                "name": "Thomas Moran",
                                "related_entities": ["Manifest Destiny"],
                            },
                            {
                                "entity_type": "political_idea",
                                "name": "Manifest Destiny",
                            },
                        ],
                    },
                )
            ]
        )

    provider._client = SimpleNamespace(messages=SimpleNamespace(create=fake_create))

    request = MuseumNotesImportRequest(
        text="Thomas Moran and Manifest Destiny",
        default_museum="National Gallery of Art",
        default_city="Washington, DC",
    )

    result = await provider.extract(request)
    assert result.source == "claude"
    assert len(result.entities) == 2
    assert result.ai_warning is None


@pytest.mark.asyncio
async def test_claude_import_timeout_falls_back_to_mock() -> None:
    provider = ClaudeMuseumNotesImportProvider("test-api-key")

    async def fake_create(**kwargs: object) -> SimpleNamespace:
        raise APITimeoutError(request=SimpleNamespace())

    provider._client = SimpleNamespace(messages=SimpleNamespace(create=fake_create))

    request = MuseumNotesImportRequest(
        text="Thomas Moran and Manifest Destiny — dramatic western landscape",
        default_museum="Smithsonian American Art Museum",
        default_city="Washington, DC",
        visit_date=date(2026, 5, 24),
    )

    result = await provider.extract(request)

    assert result.source == "mock"
    assert result.ai_warning == IMPORT_TIMEOUT_WARNING
    assert result.entities

