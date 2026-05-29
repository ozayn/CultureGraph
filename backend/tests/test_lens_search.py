"""Tests for provider-based web visual search."""

from __future__ import annotations

import logging

import pytest
import requests

from app.models import Artwork, Visit
from app.services.lens_search import (
    PROVIDER_DISPLAY_NAMES,
    PROVIDER_SEARCHAPI,
    PROVIDER_SERPAPI,
    build_lens_search_query,
    build_normalized_crop_parameter,
    get_web_visual_search_provider,
    parse_lens_candidates,
    redact_sensitive_text,
    redact_sensitive_url,
    resolve_lens_image_url,
    search_artwork_with_lens,
    unauthorized_lens_message,
)
from app.services.web_visual_search.providers.searchapi import SearchApiLensProvider
from app.services.web_visual_search.providers.serpapi import SerpApiLensProvider


def _skip_image_reachability_check(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.web_visual_search.service.verify_public_lens_image_url",
        lambda image_url, timeout=10.0: None,
    )


def test_resolve_lens_image_url_requires_upload(db_session) -> None:
    visit = Visit(museum_name="National Gallery of Art", city="Washington", visit_date="2026-01-01")
    db_session.add(visit)
    db_session.flush()
    artwork = Artwork(title="Test", visit_id=visit.id, image_url=None)
    db_session.add(artwork)
    db_session.commit()

    with pytest.raises(Exception, match="Upload a photo"):
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


def test_resolve_lens_image_url_requires_public_api_base_url(db_session, monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "public_api_base_url", None)

    visit = Visit(museum_name="National Gallery of Art", city="Washington", visit_date="2026-01-01")
    db_session.add(visit)
    db_session.flush()
    artwork = Artwork(title="Test", visit_id=visit.id, image_url="/uploads/artworks/1/photo.webp")
    db_session.add(artwork)
    db_session.commit()

    with pytest.raises(Exception, match="PUBLIC_API_BASE_URL"):
        resolve_lens_image_url(artwork)


def test_missing_serpapi_key_returns_clear_error(db_session, monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "web_visual_search_provider", PROVIDER_SERPAPI)
    monkeypatch.setattr(settings, "serpapi_api_key", None)
    monkeypatch.setattr(settings, "public_api_base_url", "https://api.example.com")
    _skip_image_reachability_check(monkeypatch)

    visit = Visit(museum_name="National Gallery of Art", city="Washington", visit_date="2026-01-01")
    db_session.add(visit)
    db_session.flush()
    artwork = Artwork(title="Test", visit_id=visit.id, image_url="/uploads/artworks/5/photo.webp")
    db_session.add(artwork)
    db_session.commit()

    with pytest.raises(Exception, match="SERPAPI_API_KEY"):
        search_artwork_with_lens(artwork)


def test_missing_searchapi_key_returns_clear_error(db_session, monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "web_visual_search_provider", PROVIDER_SEARCHAPI)
    monkeypatch.setattr(settings, "searchapi_api_key", None)
    monkeypatch.setattr(settings, "public_api_base_url", "https://api.example.com")
    _skip_image_reachability_check(monkeypatch)

    visit = Visit(museum_name="National Gallery of Art", city="Washington", visit_date="2026-01-01")
    db_session.add(visit)
    db_session.flush()
    artwork = Artwork(title="Test", visit_id=visit.id, image_url="/uploads/artworks/6/photo.webp")
    db_session.add(artwork)
    db_session.commit()

    with pytest.raises(Exception, match="SEARCHAPI_API_KEY"):
        search_artwork_with_lens(artwork)


def test_unreachable_upload_returns_clear_error(db_session, monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "web_visual_search_provider", PROVIDER_SEARCHAPI)
    monkeypatch.setattr(settings, "searchapi_api_key", "searchapi-key")
    monkeypatch.setattr(settings, "public_api_base_url", "https://api.example.com")

    visit = Visit(museum_name="National Gallery of Art", city="Washington", visit_date="2026-01-01")
    db_session.add(visit)
    db_session.flush()
    artwork = Artwork(
        title="Test",
        visit_id=visit.id,
        image_url="/uploads/artworks/7/display.webp",
        image_master_url="/uploads/artworks/7/master.webp",
        crop_x_percent=10.0,
        crop_y_percent=20.0,
        crop_width_percent=50.0,
        crop_height_percent=40.0,
    )
    db_session.add(artwork)
    db_session.commit()

    class FakeHeadResponse:
        status_code = 404

        @property
        def headers(self) -> dict[str, str]:
            return {"content-type": "application/json"}

    monkeypatch.setattr(
        "app.services.web_visual_search.validation.requests.head",
        lambda *args, **kwargs: FakeHeadResponse(),
    )

    with pytest.raises(Exception, match="not publicly reachable"):
        search_artwork_with_lens(artwork)


def test_localhost_public_base_url_is_rejected(db_session, monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "public_api_base_url", "http://localhost:8000")

    visit = Visit(museum_name="National Gallery of Art", city="Washington", visit_date="2026-01-01")
    db_session.add(visit)
    db_session.flush()
    artwork = Artwork(title="Test", visit_id=visit.id, image_url="/uploads/artworks/8/photo.webp")
    db_session.add(artwork)
    db_session.commit()

    with pytest.raises(Exception, match="non-public host"):
        resolve_lens_image_url(artwork)


def test_build_normalized_crop_parameter_from_artwork(db_session) -> None:
    visit = Visit(museum_name="National Gallery of Art", city="Washington", visit_date="2026-01-01")
    db_session.add(visit)
    db_session.flush()
    artwork = Artwork(
        title="Test",
        visit_id=visit.id,
        image_url="/uploads/artworks/1/display.webp",
        image_master_url="/uploads/artworks/1/master.webp",
        crop_x_percent=10.0,
        crop_y_percent=20.0,
        crop_width_percent=50.0,
        crop_height_percent=40.0,
    )
    db_session.add(artwork)
    db_session.commit()

    assert build_normalized_crop_parameter(artwork) == "0.1000;0.2000;0.6000;0.6000"


def test_build_normalized_crop_parameter_omits_full_image(db_session) -> None:
    visit = Visit(museum_name="National Gallery of Art", city="Washington", visit_date="2026-01-01")
    db_session.add(visit)
    db_session.flush()
    artwork = Artwork(
        title="Test",
        visit_id=visit.id,
        image_url="/uploads/artworks/1/display.webp",
        crop_x_percent=0.0,
        crop_y_percent=0.0,
        crop_width_percent=100.0,
        crop_height_percent=100.0,
    )
    db_session.add(artwork)
    db_session.commit()

    assert build_normalized_crop_parameter(artwork) is None


def test_build_lens_search_query_uses_master_with_crop(db_session, monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "public_api_base_url", "https://api.example.com")

    visit = Visit(museum_name="National Gallery of Art", city="Washington", visit_date="2026-01-01")
    db_session.add(visit)
    db_session.flush()
    artwork = Artwork(
        title="Test",
        visit_id=visit.id,
        image_url="/uploads/artworks/1/display.webp",
        image_master_url="/uploads/artworks/1/master.webp",
        crop_x_percent=10.0,
        crop_y_percent=20.0,
        crop_width_percent=50.0,
        crop_height_percent=40.0,
    )
    db_session.add(artwork)
    db_session.commit()

    query = build_lens_search_query(artwork, use_crop=True)
    assert query.image_url == "https://api.example.com/uploads/artworks/1/master.webp"
    assert query.crop == "0.1000;0.2000;0.6000;0.6000"


def test_parse_lens_candidates_maps_visual_and_exact_matches() -> None:
    payload = {
        "visual_matches": [
            {
                "position": 1,
                "title": "Starry Night",
                "link": "https://example.org/object/1",
                "source": "example.org",
                "thumbnail": "https://example.org/thumb.jpg",
                "image": "https://example.org/full.jpg",
            }
        ],
        "exact_matches": [
            {
                "position": 1,
                "title": "Exact Match",
                "link": "https://example.org/exact",
                "source": "museum.org",
                "thumbnail": "https://example.org/exact-thumb.jpg",
                "image": "https://example.org/exact-full.jpg",
            }
        ],
    }

    candidates = parse_lens_candidates(payload, max_results=12)
    assert len(candidates) == 2
    assert candidates[0].title == "Starry Night"
    assert candidates[0].confidence_label == "high"
    assert candidates[1].title == "Exact Match"
    assert candidates[1].source == "museum.org"
    assert candidates[1].confidence_label == "high"


def test_get_web_visual_search_provider_switching(monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "web_visual_search_provider", PROVIDER_SERPAPI)
    assert isinstance(get_web_visual_search_provider(), SerpApiLensProvider)

    monkeypatch.setattr(settings, "web_visual_search_provider", PROVIDER_SEARCHAPI)
    assert isinstance(get_web_visual_search_provider(), SearchApiLensProvider)

    monkeypatch.setattr(settings, "web_visual_search_provider", "unknown")
    with pytest.raises(Exception, match="Unknown WEB_VISUAL_SEARCH_PROVIDER"):
        get_web_visual_search_provider()


def test_search_artwork_with_lens_parses_serpapi_payload(db_session, monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "web_visual_search_provider", PROVIDER_SERPAPI)
    monkeypatch.setattr(settings, "serpapi_api_key", "test-key")
    monkeypatch.setattr(settings, "public_api_base_url", "https://api.example.com")
    _skip_image_reachability_check(monkeypatch)

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
        "app.services.web_visual_search.http.requests.get",
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
    assert result.provider == PROVIDER_DISPLAY_NAMES[PROVIDER_SERPAPI]


def test_search_artwork_with_lens_searchapi_sends_crop(db_session, monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "web_visual_search_provider", PROVIDER_SEARCHAPI)
    monkeypatch.setattr(settings, "searchapi_api_key", "searchapi-key")
    monkeypatch.setattr(settings, "public_api_base_url", "https://api.example.com")
    _skip_image_reachability_check(monkeypatch)

    visit = Visit(museum_name="National Gallery of Art", city="Washington", visit_date="2026-01-01")
    db_session.add(visit)
    db_session.flush()
    artwork = Artwork(
        title="Test",
        visit_id=visit.id,
        image_url="/uploads/artworks/4/display.webp",
        image_master_url="/uploads/artworks/4/master.webp",
        crop_x_percent=10.0,
        crop_y_percent=20.0,
        crop_width_percent=50.0,
        crop_height_percent=40.0,
    )
    db_session.add(artwork)
    db_session.commit()

    captured: dict = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"exact_matches": []}

    def fake_get(url, params=None, headers=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        return FakeResponse()

    monkeypatch.setattr("app.services.web_visual_search.http.requests.get", fake_get)

    result = search_artwork_with_lens(artwork)
    assert result.provider == PROVIDER_DISPLAY_NAMES[PROVIDER_SEARCHAPI]
    assert captured["params"]["engine"] == "google_lens"
    assert captured["params"]["api_key"] == "searchapi-key"
    assert captured["params"]["url"] == "https://api.example.com/uploads/artworks/4/master.webp"
    assert captured["params"]["crop"] == "0.1000;0.2000;0.6000;0.6000"


def test_lens_search_endpoint(db_session, auth_headers, monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from app.config import settings
    from app.main import app

    monkeypatch.setattr(settings, "web_visual_search_provider", PROVIDER_SERPAPI)
    monkeypatch.setattr(settings, "serpapi_api_key", "test-key")
    monkeypatch.setattr(settings, "public_api_base_url", "https://api.example.com")
    _skip_image_reachability_check(monkeypatch)

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
        "app.services.web_visual_search.http.requests.get",
        lambda *args, **kwargs: FakeResponse(),
    )

    client = TestClient(app)
    response = client.post(f"/api/artworks/{artwork.id}/lens-search", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == PROVIDER_DISPLAY_NAMES[PROVIDER_SERPAPI]
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


def test_redact_sensitive_text_masks_bearer_token() -> None:
    message = "401 Unauthorized Authorization: Bearer super-secret-token"
    redacted = redact_sensitive_text(message)
    assert "super-secret-token" not in redacted
    assert "Bearer" in redacted
    assert "REDACTED" in redacted


def test_search_artwork_with_lens_redacts_api_key_from_logs(db_session, monkeypatch, caplog) -> None:
    from app.config import settings

    secret_key = "super-secret-serpapi-key"
    monkeypatch.setattr(settings, "web_visual_search_provider", PROVIDER_SERPAPI)
    monkeypatch.setattr(settings, "serpapi_api_key", secret_key)
    monkeypatch.setattr(settings, "public_api_base_url", "https://api.example.com")
    _skip_image_reachability_check(monkeypatch)

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

    monkeypatch.setattr("app.services.web_visual_search.http.requests.get", raise_unauthorized)

    caplog.set_level(logging.WARNING)
    with pytest.raises(Exception, match=unauthorized_lens_message(PROVIDER_SERPAPI)):
        search_artwork_with_lens(artwork)

    logged = " ".join(record.getMessage() for record in caplog.records)
    assert secret_key not in logged
    assert f"api_key={secret_key}" not in logged
    assert "provider=serpapi" in logged
    assert f"artwork_id={artwork.id}" in logged
    assert "status_code=401" in logged


def test_search_artwork_with_lens_searchapi_auth_failure(db_session, monkeypatch, caplog) -> None:
    from app.config import settings

    secret_key = "super-secret-searchapi-key"
    monkeypatch.setattr(settings, "web_visual_search_provider", PROVIDER_SEARCHAPI)
    monkeypatch.setattr(settings, "searchapi_api_key", secret_key)
    monkeypatch.setattr(settings, "public_api_base_url", "https://api.example.com")
    _skip_image_reachability_check(monkeypatch)

    visit = Visit(museum_name="National Gallery of Art", city="Washington", visit_date="2026-01-01")
    db_session.add(visit)
    db_session.flush()
    artwork = Artwork(title="Test", visit_id=visit.id, image_url="/uploads/artworks/10/photo.webp")
    db_session.add(artwork)
    db_session.commit()

    def raise_forbidden(*args, **kwargs) -> None:
        response = requests.Response()
        response.status_code = 403
        response.url = (
            "https://www.searchapi.io/api/v1/search?engine=google_lens"
            f"&api_key={secret_key}&url=https%3A%2F%2Fapi.example.com%2Fuploads%2Fphoto.webp"
        )
        raise requests.HTTPError("403 Client Error: Forbidden", response=response)

    monkeypatch.setattr("app.services.web_visual_search.http.requests.get", raise_forbidden)

    caplog.set_level(logging.WARNING)
    with pytest.raises(Exception, match=unauthorized_lens_message(PROVIDER_SEARCHAPI)):
        search_artwork_with_lens(artwork)

    logged = " ".join(record.getMessage() for record in caplog.records)
    assert secret_key not in logged
    assert "provider=searchapi" in logged


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
