"""Tests for SerpApi lens search fallback."""

from __future__ import annotations

import logging

import pytest
import requests

from app.models import Artwork, Visit
from app.services.lens_search import (
    UNAUTHORIZED_LENS_MESSAGE,
    WEB_VISUAL_SEARCH_SOURCE,
    LensSearchError,
    redact_sensitive_text,
    redact_sensitive_url,
    resolve_lens_image_url,
    search_artwork_with_lens,
)


def test_resolve_lens_image_url_requires_upload(db_session) -> None:
    visit = Visit(museum_name="National Gallery of Art", city="Washington", visit_date="2026-01-01")
    db_session.add(visit)
    db_session.flush()
    artwork = Artwork(title="Test", visit_id=visit.id, image_url=None)
    db_session.add(artwork)
    db_session.commit()

    with pytest.raises(LensSearchError, match="Upload a photo"):
        resolve_lens_image_url(artwork)


def test_resolve_lens_image_url_builds_public_upload_url(db_session, monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "public_api_base_url", "https://api.example.com")

    visit = Visit(museum_name="National Gallery of Art", city="Washington", visit_date="2026-01-01")
    db_session.add(visit)
    db_session.flush()
    artwork = Artwork(title="Test", visit_id=visit.id, image_url="/uploads/artworks/1/photo.webp")
    db_session.add(artwork)
    db_session.commit()

    assert (
        resolve_lens_image_url(artwork)
        == "https://api.example.com/uploads/artworks/1/photo.webp"
    )


def test_resolve_lens_image_url_accepts_https(db_session) -> None:
    visit = Visit(museum_name="National Gallery of Art", city="Washington", visit_date="2026-01-01")
    db_session.add(visit)
    db_session.flush()
    artwork = Artwork(
        title="Test",
        visit_id=visit.id,
        image_url="https://example.org/art.jpg",
    )
    db_session.add(artwork)
    db_session.commit()

    assert resolve_lens_image_url(artwork) == "https://example.org/art.jpg"


def test_search_artwork_with_lens_parses_serpapi_payload(db_session, monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "serpapi_api_key", "test-key")
    monkeypatch.setattr(settings, "public_api_base_url", "https://api.example.com")

    visit = Visit(museum_name="National Gallery of Art", city="Washington", visit_date="2026-01-01")
    db_session.add(visit)
    db_session.flush()
    artwork = Artwork(title="Test", visit_id=visit.id, image_url="/uploads/artworks/2/photo.webp")
    db_session.add(artwork)
    db_session.commit()

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "visual_matches": [
                    {
                        "position": 1,
                        "title": "Starry Night",
                        "link": "https://example.org/object/1",
                        "source": "example.org",
                        "thumbnail": "https://example.org/thumb.jpg",
                        "image": "https://example.org/full.jpg",
                    }
                ]
            }

    monkeypatch.setattr(
        "app.services.lens_search.requests.get",
        lambda *args, **kwargs: FakeResponse(),
    )

    result = search_artwork_with_lens(artwork)
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.title == "Starry Night"
    assert candidate.source == "example.org"
    assert candidate.source_url == "https://example.org/object/1"
    assert candidate.source_rank == 1
    assert candidate.confidence_label == "high"
    assert result.provider == WEB_VISUAL_SEARCH_SOURCE


def test_lens_search_endpoint(db_session, auth_headers, monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from app.config import settings
    from app.main import app

    monkeypatch.setattr(settings, "serpapi_api_key", "test-key")
    monkeypatch.setattr(settings, "public_api_base_url", "https://api.example.com")

    visit = Visit(museum_name="National Gallery of Art", city="Washington", visit_date="2026-01-01")
    db_session.add(visit)
    db_session.flush()
    artwork = Artwork(title="Test", visit_id=visit.id, image_url="/uploads/artworks/3/photo.webp")
    db_session.add(artwork)
    db_session.commit()

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"visual_matches": []}

    monkeypatch.setattr(
        "app.services.lens_search.requests.get",
        lambda *args, **kwargs: FakeResponse(),
    )

    client = TestClient(app)
    response = client.post(f"/api/artworks/{artwork.id}/lens-search", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == WEB_VISUAL_SEARCH_SOURCE
    assert payload["candidates"] == []
    assert "third-party" in payload["disclaimer"]


def test_redact_sensitive_url_masks_api_key() -> None:
    url = "https://serpapi.com/search.json?engine=google_lens&api_key=super-secret&url=https%3A%2F%2Fexample.com"
    redacted = redact_sensitive_url(url)
    assert "super-secret" not in redacted
    assert "api_key=" in redacted
    assert "REDACTED" in redacted


def test_redact_sensitive_text_masks_api_key_in_exception_message() -> None:
    message = (
        "401 Client Error: Unauthorized for url: "
        "https://serpapi.com/search.json?api_key=super-secret&engine=google_lens"
    )
    redacted = redact_sensitive_text(message)
    assert "super-secret" not in redacted
    assert "api_key=" in redacted
    assert "REDACTED" in redacted


def test_search_artwork_with_lens_redacts_api_key_from_logs(db_session, monkeypatch, caplog) -> None:
    from app.config import settings

    secret_key = "super-secret-serpapi-key"
    monkeypatch.setattr(settings, "serpapi_api_key", secret_key)
    monkeypatch.setattr(settings, "public_api_base_url", "https://api.example.com")

    visit = Visit(museum_name="National Gallery of Art", city="Washington", visit_date="2026-01-01")
    db_session.add(visit)
    db_session.flush()
    artwork = Artwork(title="Test", visit_id=visit.id, image_url="/uploads/artworks/9/photo.webp")
    db_session.add(artwork)
    db_session.commit()

    def raise_unauthorized(*args, **kwargs) -> None:
        response = requests.Response()
        response.status_code = 401
        response.url = (
            "https://serpapi.com/search.json?engine=google_lens"
            f"&api_key={secret_key}&url=https%3A%2F%2Fapi.example.com%2Fuploads%2Fphoto.webp"
        )
        raise requests.HTTPError("401 Client Error: Unauthorized", response=response)

    monkeypatch.setattr("app.services.lens_search.requests.get", raise_unauthorized)

    caplog.set_level(logging.WARNING)
    with pytest.raises(LensSearchError, match=UNAUTHORIZED_LENS_MESSAGE):
        search_artwork_with_lens(artwork)

    logged = " ".join(record.getMessage() for record in caplog.records)
    assert secret_key not in logged
    assert f"api_key={secret_key}" not in logged
    assert "provider=serpapi" in logged
    assert f"artwork_id={artwork.id}" in logged
    assert "status_code=401" in logged


def test_lens_search_endpoint_requires_auth(db_session) -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    visit = Visit(museum_name="National Gallery of Art", city="Washington", visit_date="2026-01-01")
    db_session.add(visit)
    db_session.flush()
    artwork = Artwork(title="Test", visit_id=visit.id, image_url="/uploads/art.webp")
    db_session.add(artwork)
    db_session.commit()

    client = TestClient(app)
    response = client.post(f"/api/artworks/{artwork.id}/lens-search")
    assert response.status_code == 401
