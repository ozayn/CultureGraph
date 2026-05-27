"""Tests for artwork AI enrichment endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models import Artwork
from app.services.artwork_enrichment import ENRICHMENT_STATUS_COMPLETED, run_artwork_enrichment


@pytest.mark.asyncio
async def test_start_enrichment_requires_image(auth_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        visit = await client.post(
            "/api/visits",
            headers=auth_headers,
            json={
                "museum_name": "Test Museum",
                "city": "Washington, DC",
                "visit_date": "2026-05-25",
            },
        )
        artwork = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "Enrichment artwork", "visit_id": visit.json()["id"]},
        )
        artwork_id = artwork.json()["id"]

        unauth = await client.post(f"/api/artworks/{artwork_id}/enrichment")
        assert unauth.status_code == 401

        missing_image = await client.post(
            f"/api/artworks/{artwork_id}/enrichment",
            headers=auth_headers,
        )
        assert missing_image.status_code == 400


@pytest.mark.asyncio
async def test_enrichment_status_returns_research_draft(
    auth_headers: dict[str, str],
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.research import MockLLMProvider

    monkeypatch.setattr(
        "app.services.artwork_enrichment.get_research_provider",
        lambda: MockLLMProvider(),
    )

    artwork = Artwork(
        title=None,
        visit_id=None,
        image_url="/uploads/artworks/1/example.webp",
    )
    db_session.add(artwork)
    db_session.commit()
    db_session.refresh(artwork)

    await run_artwork_enrichment(db_session, artwork.id)
    db_session.refresh(artwork)
    assert artwork.enrichment_status == ENRICHMENT_STATUS_COMPLETED

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        status = await client.get(f"/api/artworks/{artwork.id}/enrichment")
        assert status.status_code == 200
        payload = status.json()
        assert payload["status"] == ENRICHMENT_STATUS_COMPLETED
        assert payload["draft"] is not None
        assert payload["draft"]["short_summary"]
