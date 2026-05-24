from datetime import date
from types import SimpleNamespace

import pytest

from app.config import settings
from app.schemas import MuseumNotesImportRequest
from app.services.museum_notes_import import (
    ClaudeMuseumNotesImportProvider,
    IMPORT_FALLBACK_WARNING,
    IMPORT_TOOL_NAME,
    _read_claude_import_payload,
)
from app.services.research import ResearchProviderError


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
                    "entities": [],
                    "concept_links": [],
                },
            )
        ]
    )
    payload = _read_claude_import_payload(message)
    assert payload["visit"]["museum_name"] == "NGA"


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
            content=[SimpleNamespace(type="text", text="Sorry, I cannot produce JSON right now.")]
        )

    provider._client = SimpleNamespace(messages=SimpleNamespace(create=fake_create))

    request = MuseumNotesImportRequest(
        text="Thomas Moran and Manifest Destiny",
        default_museum="Smithsonian American Art Museum",
        default_city="Washington, DC",
    )

    with pytest.raises(ResearchProviderError, match="could not be parsed"):
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
                    input={"visit": {"museum_name": "NGA"}, "entities": [], "concept_links": []},
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
