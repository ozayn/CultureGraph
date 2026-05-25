import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas import AiSuggestedAnnotation, ResearchDraft, SuggestedAnnotationPosition
from app.services.research import MockLLMProvider


@pytest.mark.asyncio
async def test_research_returns_structured_suggested_annotations(
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.routers.research.get_research_provider",
        lambda: MockLLMProvider(),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        visit_response = await client.post(
            "/api/visits",
            headers=auth_headers,
            json={
                "museum_name": "Test Museum",
                "city": "Washington, DC",
                "visit_date": "2026-05-25",
            },
        )
        visit_id = visit_response.json()["id"]

        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "Research artwork", "visit_id": visit_id},
        )
        artwork_id = artwork_response.json()["id"]

        research_response = await client.post(
            f"/api/artworks/{artwork_id}/research",
            headers=auth_headers,
        )

    assert research_response.status_code == 200
    payload = research_response.json()
    assert payload["suggested_annotations"]
    first = payload["suggested_annotations"][0]
    assert "note" in first
    assert "tags" in first
    assert "linked_concept_names" in first
    assert "confidence" in first
    assert "suggested_position" in first
    assert first["suggested_position"]["x_percent"] is None or isinstance(
        first["suggested_position"]["x_percent"], (int, float)
    )


@pytest.mark.asyncio
async def test_mock_research_provider_includes_nullable_coordinates() -> None:
    draft = await MockLLMProvider().generate_research({"title": "Test"})
    assert isinstance(draft, ResearchDraft)
    assert draft.suggested_annotations
    positioned = [
        item
        for item in draft.suggested_annotations
        if item.suggested_position.x_percent is not None
    ]
    unpositioned = [
        item
        for item in draft.suggested_annotations
        if item.suggested_position.x_percent is None
    ]
    assert positioned
    assert unpositioned


def test_ai_suggested_annotation_normalizes_legacy_text_field() -> None:
    item = AiSuggestedAnnotation.model_validate(
        {
            "category": "history",
            "text": "Legacy note text",
            "confidence": 0.7,
        }
    )
    assert item.note == "Legacy note text"


def test_suggested_position_clears_partial_coordinates() -> None:
    position = SuggestedAnnotationPosition.model_validate(
        {"x_percent": 40.0, "y_percent": None, "reason": "Uncertain"}
    )
    assert position.x_percent is None
    assert position.y_percent is None
