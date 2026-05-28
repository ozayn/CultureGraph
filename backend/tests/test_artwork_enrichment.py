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


@pytest.mark.asyncio
async def test_legacy_enrichment_synthesizes_visual_hypothesis(db_session) -> None:
    from app.models import ResearchNote
    from app.services.artwork_enrichment import (
        ENRICHMENT_STATUS_COMPLETED,
        synthesize_legacy_identification,
    )

    artwork = Artwork(
        title="Unknown",
        visit_id=None,
        image_url="/uploads/artworks/99/example.webp",
        enrichment_status=ENRICHMENT_STATUS_COMPLETED,
        enrichment_lookup={
            "candidates": [],
            "sources_searched": ["National Gallery of Art"],
            "query_used": "Four Dancers · Edgar Degas",
            "query_source": "ai_title",
        },
    )
    db_session.add(artwork)
    db_session.flush()

    note = ResearchNote(
        artwork_id=artwork.id,
        short_summary="Four Dancers — possibly by Edgar Degas (Impressionism).",
        historical_context="Degas returned repeatedly to ballet rehearsal rooms.",
        visual_elements_to_notice='["Grouped dancers"]',
        related_questions='["Which museum holds this pastel?"]',
        suggested_annotations="[]",
        possible_title="Four Dancers",
        possible_artist="Edgar Degas",
    )
    db_session.add(note)
    db_session.commit()
    db_session.refresh(artwork)

    synthesized = synthesize_legacy_identification(None)
    assert synthesized is None

    from app.services.artwork_enrichment import latest_research_draft

    draft, _ = latest_research_draft(db_session, artwork.id)
    synthesized = synthesize_legacy_identification(draft)
    assert synthesized is not None
    assert synthesized.identification_mode == "style_subject"
    assert synthesized.identification_mode != "catalog_match"
    assert synthesized.visual_hypothesis_title == "Four Dancers"
    assert synthesized.visual_hypothesis_artist == "Edgar Degas"
    assert "AI visual hypothesis" in synthesized.display_summary
    assert "Not verified against collection records" in synthesized.display_summary

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/artworks/{artwork.id}/enrichment")
        assert response.status_code == 200
        payload = response.json()
        identification = payload["identification"]
        assert identification is not None
        assert identification["identification_mode"] == "style_subject"
        assert identification["visual_hypothesis_title"] == "Four Dancers"
        assert identification["visual_hypothesis_artist"] == "Edgar Degas"
        assert identification["suggested_title"] is None
        assert identification["catalog_title"] is None
