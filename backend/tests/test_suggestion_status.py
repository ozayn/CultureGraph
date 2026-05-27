import json

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import Annotation, ResearchNote
from app.services.suggested_annotations import (
    infer_accepted_suggestions,
    load_note_suggestions,
    parse_suggested_annotations_json,
    pending_suggestions,
    save_note_suggestions,
)
from app.schemas import AiSuggestedAnnotation, SuggestedAnnotationPosition


def _pending_suggestion(note: str = "Notice the central axis.") -> AiSuggestedAnnotation:
    return AiSuggestedAnnotation(
        category="composition",
        note=note,
        tags=["composition"],
        linked_concept_names=[],
        confidence=0.72,
        suggested_position=SuggestedAnnotationPosition(
            x_percent=42.0,
            y_percent=38.0,
            reason="Focal area",
        ),
    )


def test_parse_suggestions_defaults_status_to_pending() -> None:
    raw = json.dumps(
        [
            {
                "category": "history",
                "note": "Research the patron.",
                "confidence": 0.6,
            }
        ]
    )
    items = parse_suggested_annotations_json(raw)
    assert len(items) == 1
    assert items[0].status == "pending"
    assert items[0].accepted_annotation_id is None


def test_infer_accepted_from_matching_annotation() -> None:
    suggestion = _pending_suggestion()
    annotation = Annotation(
        artwork_id=1,
        x_percent=10.0,
        y_percent=20.0,
        category="composition",
        text=suggestion.note,
        tags="[]",
        linked_entity_ids="[]",
        linked_concept_names="[]",
    )
    annotation.id = 99

    inferred = infer_accepted_suggestions([suggestion], [annotation])
    assert inferred[0].status == "accepted"
    assert inferred[0].accepted_annotation_id == 99


def test_pending_suggestions_excludes_accepted_and_dismissed() -> None:
    pending = _pending_suggestion()
    accepted = pending.model_copy(update={"status": "accepted", "accepted_annotation_id": 1})
    dismissed = pending.model_copy(update={"status": "dismissed"})
    result = pending_suggestions([pending, accepted, dismissed])
    assert len(result) == 1
    assert result[0].status == "pending"


@pytest.mark.asyncio
async def test_patch_research_suggestions_persists_status(
    auth_headers: dict[str, str],
    db_session: Session,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "Suggestion status artwork", "visit_id": None},
        )
        artwork_id = artwork_response.json()["id"]

        suggestion = _pending_suggestion()
        note = ResearchNote(
            artwork_id=artwork_id,
            short_summary="Summary",
            historical_context="Context",
            visual_elements_to_notice="[]",
            related_questions="[]",
            suggested_annotations=json.dumps(
                [suggestion.model_dump(mode="json")]
            ),
        )
        db_session.add(note)
        db_session.commit()
        db_session.refresh(note)
        note_id = note.id

        accepted = suggestion.model_copy(
            update={"status": "accepted", "accepted_annotation_id": 42}
        )
        patch_response = await client.patch(
            f"/api/artworks/{artwork_id}/research/{note_id}/suggestions",
            headers=auth_headers,
            json={"suggested_annotations": [accepted.model_dump(mode="json")]},
        )
        assert patch_response.status_code == 200

        notes_response = await client.get(f"/api/artworks/{artwork_id}/research")
        assert notes_response.status_code == 200
        stored = json.loads(notes_response.json()[0]["suggested_annotations"])
        assert stored[0]["status"] == "accepted"
        assert stored[0]["accepted_annotation_id"] == 42
        assert pending_suggestions(parse_suggested_annotations_json(json.dumps(stored))) == []


@pytest.mark.asyncio
async def test_list_research_migrates_matching_annotation_to_accepted(
    auth_headers: dict[str, str],
    db_session: Session,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "Infer accepted artwork", "visit_id": None},
        )
        artwork_id = artwork_response.json()["id"]

        suggestion = _pending_suggestion("Matching saved annotation text.")
        note = ResearchNote(
            artwork_id=artwork_id,
            short_summary="Summary",
            historical_context="Context",
            visual_elements_to_notice="[]",
            related_questions="[]",
            suggested_annotations=json.dumps(
                [suggestion.model_dump(mode="json")]
            ),
        )
        db_session.add(note)
        db_session.flush()

        db_session.add(
            Annotation(
                artwork_id=artwork_id,
                x_percent=12.0,
                y_percent=34.0,
                category="composition",
                text="Matching saved annotation text.",
                tags="[]",
                linked_entity_ids="[]",
                linked_concept_names="[]",
            )
        )
        db_session.commit()

        notes_response = await client.get(f"/api/artworks/{artwork_id}/research")
        assert notes_response.status_code == 200
        stored = json.loads(notes_response.json()[0]["suggested_annotations"])
        assert stored[0]["status"] == "accepted"
        assert isinstance(stored[0]["accepted_annotation_id"], int)


@pytest.mark.asyncio
async def test_accept_annotation_then_reload_hides_pending_suggestion(
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.research import MockLLMProvider

    monkeypatch.setattr(
        "app.routers.research.get_research_provider",
        lambda: MockLLMProvider(),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "Accept flow artwork", "visit_id": None},
        )
        artwork_id = artwork_response.json()["id"]

        research_response = await client.post(
            f"/api/artworks/{artwork_id}/research",
            headers=auth_headers,
        )
        assert research_response.status_code == 200
        suggestion = research_response.json()["suggested_annotations"][0]

        notes_response = await client.get(f"/api/artworks/{artwork_id}/research")
        note_id = notes_response.json()[0]["id"]

        annotation_response = await client.post(
            f"/api/artworks/{artwork_id}/annotations",
            headers=auth_headers,
            json={
                "x_percent": suggestion["suggested_position"]["x_percent"],
                "y_percent": suggestion["suggested_position"]["y_percent"],
                "category": suggestion["category"],
                "text": suggestion["note"],
                "tags": suggestion["tags"],
                "linked_entity_ids": [],
                "linked_concept_names": suggestion["linked_concept_names"],
            },
        )
        assert annotation_response.status_code == 201
        annotation_id = annotation_response.json()["id"]

        accepted_payload = {
            **suggestion,
            "status": "accepted",
            "accepted_annotation_id": annotation_id,
        }
        patch_response = await client.patch(
            f"/api/artworks/{artwork_id}/research/{note_id}/suggestions",
            headers=auth_headers,
            json={"suggested_annotations": [accepted_payload]},
        )
        assert patch_response.status_code == 200

        reload_response = await client.get(f"/api/artworks/{artwork_id}/research")
        stored = json.loads(reload_response.json()[0]["suggested_annotations"])
        assert pending_suggestions(parse_suggested_annotations_json(json.dumps(stored))) == []

        annotations_response = await client.get(
            f"/api/artworks/{artwork_id}/annotations"
        )
        assert any(item["id"] == annotation_id for item in annotations_response.json())
