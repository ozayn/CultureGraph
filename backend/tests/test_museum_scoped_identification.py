"""Museum-scoped artwork identification and lookup routing."""

from __future__ import annotations

from httpx import ASGITransport, AsyncClient
import pytest

from app.main import app
from app.schemas import ArtworkLookupCandidateRead, ArtworkLookupResponse, ResearchDraft
from app.services.artwork_identification import build_identification, rerank_candidates_with_visual
from app.services.artwork_lookup import lookup_artwork_candidates
from app.services.lookup_response import lookup_response_from_result
from app.services.lookup_types import LookupResult
from app.services.visual_analysis import VisualAnalysis
from app.sources.base import ArtworkLookupQuery
from app.sources.museums import MET_SOURCE_NAME, NGA_SOURCE_NAME
from app.sources.routing import (
    museum_collection_display_name,
    museum_short_label,
    resolve_lookup_sources,
)


def test_nga_visit_routes_to_nga_only() -> None:
    query = ArtworkLookupQuery(
        title="Bathers",
        artist=None,
        museum_name="National Gallery of Art",
    )
    assert resolve_lookup_sources(query) == ["nga"]
    assert museum_collection_display_name(query.museum_name) == NGA_SOURCE_NAME
    assert museum_short_label(NGA_SOURCE_NAME) == "NGA"


def test_unrecognized_museum_does_not_search_all_by_default() -> None:
    query = ArtworkLookupQuery(
        title="Some work",
        artist=None,
        museum_name="British Museum",
    )
    assert resolve_lookup_sources(query) == []


def test_no_museum_context_does_not_search_by_default() -> None:
    query = ArtworkLookupQuery(title="Some work", artist=None, museum_name=None)
    assert resolve_lookup_sources(query) == []


def test_broaden_source_searches_all_museums() -> None:
    query = ArtworkLookupQuery(
        title="Some work",
        artist=None,
        museum_name="National Gallery of Art",
        source="all",
    )
    assert set(resolve_lookup_sources(query)) == {"nga", "smithsonian", "met", "aic"}


def test_museum_rerank_prefers_visit_collection() -> None:
    visual = VisualAnalysis(
        subject="dancers on stage",
        visual_tags=["ballet", "performance"],
    )
    candidates = [
        ArtworkLookupCandidateRead(
            title="The Dance Class",
            artist="Edgar Degas",
            date="1874",
            medium="oil on canvas",
            image_url=None,
            object_url="https://example.com/nga",
            accession_number="1",
            source_name=NGA_SOURCE_NAME,
            confidence=0.55,
            rights_label=None,
        ),
        ArtworkLookupCandidateRead(
            title="The Large Bathers",
            artist="Paul Cézanne",
            date="1906",
            medium="oil on canvas",
            image_url=None,
            object_url="https://example.com/met",
            accession_number="2",
            source_name=MET_SOURCE_NAME,
            confidence=0.58,
            rights_label=None,
        ),
    ]
    lookup = ArtworkLookupResponse(
        candidates=candidates,
        sources_searched=[NGA_SOURCE_NAME],
        search_scope="museum",
        museum_collection_name=NGA_SOURCE_NAME,
    )
    draft = ResearchDraft(
        short_summary="",
        historical_context="",
        visual_elements_to_notice=[],
        related_questions=[],
    )

    reranked = rerank_candidates_with_visual(
        candidates,
        visual,
        ["ballet", "dancers", "performance"],
        draft=draft,
        lookup=lookup,
        visit_museum_name="National Gallery of Art",
    )

    assert reranked[0].source_name == NGA_SOURCE_NAME
    assert reranked[0].confidence <= 0.58


def test_visual_tags_affect_ranking_not_confidence_inflation() -> None:
    visual = VisualAnalysis(
        subject="dancers on stage",
        visual_tags=["ballet", "performance"],
    )
    base = ArtworkLookupCandidateRead(
        title="The Dance Class",
        artist="Edgar Degas",
        date="1874",
        medium="oil on canvas",
        image_url=None,
        object_url="https://example.com/nga",
        accession_number="1",
        source_name=NGA_SOURCE_NAME,
        confidence=0.42,
        rights_label=None,
    )
    lookup = ArtworkLookupResponse(
        candidates=[base],
        sources_searched=[NGA_SOURCE_NAME],
        search_scope="museum",
        museum_collection_name=NGA_SOURCE_NAME,
    )
    draft = ResearchDraft(
        short_summary="",
        historical_context="",
        visual_elements_to_notice=[],
        related_questions=[],
    )

    reranked = rerank_candidates_with_visual(
        [base],
        visual,
        ["ballet", "dancers"],
        draft=draft,
        lookup=lookup,
    )
    identification = build_identification(
        draft,
        lookup.model_copy(update={"candidates": reranked}),
        visual,
        visit_museum_name="National Gallery of Art",
    )

    assert identification.confidence_level != "high"
    assert identification.identification_mode != "catalog_match"


def test_build_identification_uses_possible_nga_candidates_copy() -> None:
    lookup = lookup_response_from_result(
        LookupResult(
            candidates=[
                ArtworkLookupCandidateRead(
                    title="Study for a Portrait",
                    artist="Unknown",
                    date="1900",
                    medium="oil",
                    image_url=None,
                    object_url="https://example.com",
                    accession_number="1",
                    source_name=NGA_SOURCE_NAME,
                    confidence=0.4,
                    rights_label=None,
                    low_confidence=True,
                    match_tier="weak",
                )
            ],
            related_candidates=[],
            query_strategy="broad",
        ),
        query=ArtworkLookupQuery(
            title=None,
            artist=None,
            museum_name="National Gallery of Art",
        ),
        query_used="portrait study",
        query_source="visual_keywords",
        visual_keywords=True,
        visit_museum_name="National Gallery of Art",
    )
    draft = ResearchDraft(
        short_summary="",
        historical_context="",
        visual_elements_to_notice=[],
        related_questions=[],
    )
    visual = VisualAnalysis(subject="portrait study")

    identification = build_identification(
        draft,
        lookup,
        visual,
        visit_museum_name="National Gallery of Art",
    )

    assert "Possible NGA candidates" in identification.display_summary
    assert identification.identification_mode == "possible_match"


def test_lookup_without_wikimedia_fallback_when_museum_empty() -> None:
    query = ArtworkLookupQuery(
        title="ZZZZZZ Nonexistent Unique Title 99999",
        artist="Nobody Known",
        museum_name="National Gallery of Art",
        has_title_query=True,
    )
    result = lookup_artwork_candidates(query, allow_wikimedia_fallback=False)
    assert all(
        candidate.source_name != "Wikimedia Commons"
        for candidate in [*result.candidates, *result.related_candidates]
    )


@pytest.mark.asyncio
async def test_nga_visit_lookup_searches_nga_first(auth_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        visit_response = await client.post(
            "/api/visits",
            headers=auth_headers,
            json={
                "museum_name": "National Gallery of Art",
                "city": "Washington, DC",
                "visit_date": "2026-05-25",
            },
        )
        visit_id = visit_response.json()["id"]

        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "George Washington", "artist": "Stuart", "visit_id": visit_id},
        )
        artwork_id = artwork_response.json()["id"]

        lookup_response = await client.get(
            f"/api/artworks/{artwork_id}/lookup-image",
            headers=auth_headers,
        )

    payload = lookup_response.json()
    assert lookup_response.status_code == 200
    assert payload["sources_searched"] == [NGA_SOURCE_NAME]
    assert payload["search_scope"] == "museum"
    assert payload["museum_collection_name"] == NGA_SOURCE_NAME


@pytest.mark.asyncio
async def test_unrecognized_museum_requires_broaden_for_multi_source(
    auth_headers: dict[str, str],
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        visit_response = await client.post(
            "/api/visits",
            headers=auth_headers,
            json={
                "museum_name": "British Museum",
                "city": "London",
                "visit_date": "2026-05-25",
            },
        )
        visit_id = visit_response.json()["id"]

        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "Some artwork", "visit_id": visit_id},
        )
        artwork_id = artwork_response.json()["id"]

        scoped = await client.get(
            f"/api/artworks/{artwork_id}/lookup-image",
            headers=auth_headers,
        )
        broadened = await client.get(
            f"/api/artworks/{artwork_id}/lookup-image",
            headers=auth_headers,
            params={"broaden_sources": "true"},
        )

    assert scoped.status_code == 200
    assert scoped.json()["sources_searched"] == []

    assert broadened.status_code == 200
    assert len(broadened.json()["sources_searched"]) >= 2
    assert broadened.json()["search_scope"] == "broad"
