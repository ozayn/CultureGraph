import io

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app
from app.services.audio_interpretation import AudioInterpretationDraft, get_interpretation_provider


def _tiny_wav_bytes() -> bytes:
  # Minimal valid-enough WAV header + silence for upload tests.
  return (
    b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
    b"\x44\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
  )


@pytest.mark.asyncio
async def test_create_audio_note_metadata(auth_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        visit_response = await client.post(
            "/api/visits",
            headers=auth_headers,
            json={
                "museum_name": "Audio Museum",
                "city": "Washington, DC",
                "visit_date": "2026-05-25",
            },
        )
        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={
                "title": "Audio note artwork",
                "visit_id": visit_response.json()["id"],
            },
        )
        artwork_id = artwork_response.json()["id"]

        upload_response = await client.post(
            "/api/audio-notes",
            headers=auth_headers,
            data={"artwork_id": str(artwork_id), "duration_seconds": "12.5"},
            files={"file": ("note.wav", _tiny_wav_bytes(), "audio/wav")},
        )

    assert upload_response.status_code == 201
    payload = upload_response.json()
    assert payload["artwork_id"] == artwork_id
    assert payload["audio_url"].startswith("/uploads/audio-notes/")
    assert payload["duration_seconds"] == 12.5
    assert payload["transcript"] is None
    assert payload["interpretation"] is None


@pytest.mark.asyncio
async def test_reject_unsupported_audio_type(auth_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "Audio reject"},
        )
        artwork_id = artwork_response.json()["id"]

        upload_response = await client.post(
            "/api/audio-notes",
            headers=auth_headers,
            data={"artwork_id": str(artwork_id)},
            files={"file": ("note.txt", b"not audio", "text/plain")},
        )

    assert upload_response.status_code == 415


@pytest.mark.asyncio
async def test_reject_oversized_audio(auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "audio_note_max_bytes", 32)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "Oversized audio"},
        )
        artwork_id = artwork_response.json()["id"]

        upload_response = await client.post(
            "/api/audio-notes",
            headers=auth_headers,
            data={"artwork_id": str(artwork_id)},
            files={"file": ("note.wav", b"x" * 64, "audio/wav")},
        )

    assert upload_response.status_code == 413


@pytest.mark.asyncio
async def test_transcribe_fallback_without_openai_key(
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "openai_api_key", None)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "Transcribe fallback"},
        )
        artwork_id = artwork_response.json()["id"]
        upload_response = await client.post(
            "/api/audio-notes",
            headers=auth_headers,
            data={"artwork_id": str(artwork_id)},
            files={"file": ("note.wav", _tiny_wav_bytes(), "audio/wav")},
        )
        note_id = upload_response.json()["id"]

        transcribe_response = await client.post(
            f"/api/audio-notes/{note_id}/transcribe",
            headers=auth_headers,
        )

    assert transcribe_response.status_code == 503
    assert "OPENAI_API_KEY" in transcribe_response.json()["detail"]


@pytest.mark.asyncio
async def test_manual_farsi_transcript_detects_language(
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "openai_api_key", None)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "Farsi note"},
        )
        artwork_id = artwork_response.json()["id"]
        upload_response = await client.post(
            "/api/audio-notes",
            headers=auth_headers,
            data={"artwork_id": str(artwork_id)},
            files={"file": ("note.wav", _tiny_wav_bytes(), "audio/wav")},
        )
        note_id = upload_response.json()["id"]

        transcribe_response = await client.post(
            f"/api/audio-notes/{note_id}/transcribe",
            headers=auth_headers,
            json={"transcript_original": "لباس قرمز و چهره رسمی کودک را می‌بینم."},
        )

    assert transcribe_response.status_code == 200
    payload = transcribe_response.json()
    assert payload["detected_language"] == "fa"
    assert payload["transcript_original"].startswith("لباس")


@pytest.mark.asyncio
async def test_manual_transcript_and_interpretation_placeholder(
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "anthropic_api_key", None)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "Interpret note"},
        )
        artwork_id = artwork_response.json()["id"]
        upload_response = await client.post(
            "/api/audio-notes",
            headers=auth_headers,
            data={"artwork_id": str(artwork_id)},
            files={"file": ("note.wav", _tiny_wav_bytes(), "audio/wav")},
        )
        note_id = upload_response.json()["id"]

        transcribe_response = await client.post(
            f"/api/audio-notes/{note_id}/transcribe",
            headers=auth_headers,
            json={"transcript": "I notice the red clothing and formal pose."},
        )
        assert transcribe_response.status_code == 200
        assert transcribe_response.json()["transcript"].startswith("I notice")

        interpret_response = await client.post(
            f"/api/audio-notes/{note_id}/interpret",
            headers=auth_headers,
        )

    assert interpret_response.status_code == 200
    payload = interpret_response.json()
    assert payload["cleaned_note"]
    assert payload["interpretation"]["cleaned_note"]
    assert payload["interpretation"]["observations"]


def test_interpretation_json_validates_bilingual_fields() -> None:
    draft = AudioInterpretationDraft.model_validate(
        {
            "cleaned_note": "The child looks aristocratic.",
            "cleaned_note_original_language": "کودک اشرافی به نظر می‌رسد.",
            "observations": ["Formal red clothing"],
            "visual_elements": ["red fabric"],
            "questions": ["Who is the child?"],
            "tags": ["portrait"],
            "tag_aliases": ["لباس قرمز"],
            "suggested_annotations": [
                {
                    "category": "observation",
                    "note": "Formal red clothing suggests status.",
                    "tags": ["clothing"],
                    "linked_concept_names": ["aristocracy"],
                }
            ],
            "related_entities": ["aristocracy"],
        }
    )
    provider = get_interpretation_provider()
    assert provider is not None
    assert draft.cleaned_note.startswith("The child")
    assert draft.cleaned_note_original_language
    assert draft.tag_aliases == ["لباس قرمز"]


@pytest.mark.asyncio
async def test_public_cannot_upload_audio_note() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/audio-notes",
            data={"artwork_id": "1"},
            files={"file": ("note.wav", _tiny_wav_bytes(), "audio/wav")},
        )

    assert response.status_code == 401
