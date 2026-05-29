"""Semantic artwork retrieval — normalization, expansion, and Degas dancer ranking."""

from __future__ import annotations

from dataclasses import replace

from app.schemas import ArtworkLookupCandidateRead, ArtworkLookupResponse, ResearchDraft, VisualAnalysisRead
from app.services.artwork_identification import build_identification
from app.services.lookup_query import build_exact_artwork_lookup_query
from app.services.lookup_ranking import rank_lookup_candidates
from app.services.lookup_stages import lookup_artwork_candidates_staged
from app.services.semantic_retrieval import (
    expand_artwork_search_terms,
    normalize_catalog_title,
    semantic_title_similarity,
)
from app.services.visual_analysis import VisualAnalysis, collect_exact_artwork_keywords
from app.sources.base import ArtworkLookupCandidate, ArtworkLookupQuery
from app.sources.museums import NGA_SOURCE_NAME


def test_normalize_catalog_title_strips_study_prefix_and_numbering() -> None:
    assert normalize_catalog_title("Study for Four Dancers") == "4 dancers"
    assert normalize_catalog_title("After Edgar Degas — Dancers, No. 2") == "edgar degas dancers"
    assert normalize_catalog_title("Untitled") == ""


def test_expand_four_dancers_query_includes_ballet_phrases() -> None:
    terms = expand_artwork_search_terms(title="Four Dancers", artist="Edgar Degas")

    blob = " ".join(terms).lower()
    assert "four dancers" in blob
    assert "dancers" in blob
    assert "ballet dancers" in blob
    assert "four figures" in blob
    assert "degas dancers" in blob
    assert "ballet rehearsal" in blob
    assert "pastel dancers" in blob
    assert "edgar degas" in blob


def test_semantic_title_similarity_matches_alternate_catalog_titles() -> None:
    assert semantic_title_similarity("Four Dancers", "Ballet Rehearsal") >= 0.12
    assert semantic_title_similarity("Four Dancers", "Study for Dancers") >= 0.22
    assert semantic_title_similarity("Four Dancers", "Portrait of Henri Valpinçon") <= 0.22


def test_semantic_ranking_prefers_dance_deg_over_unrelated_portrait() -> None:
    query = ArtworkLookupQuery(
        title="Four Dancers",
        artist="Edgar Degas",
        museum_name="National Gallery of Art",
        has_title_query=True,
        semantic_search=True,
        expanded_search_terms=tuple(
            expand_artwork_search_terms(title="Four Dancers", artist="Edgar Degas")
        ),
        expected_medium_type="2d",
        medium_type_filter="2d",
    )

    raw = [
        (
            0.4,
            {
                "title": "Portrait of Henri Valpinçon",
                "artist": "Edgar Degas",
                "medium": "oil on canvas",
            },
            ArtworkLookupCandidate(
                title="Portrait of Henri Valpinçon",
                artist="Edgar Degas",
                date="1868",
                medium="oil on canvas",
                image_url=None,
                object_url="https://example.org/portrait",
                accession_number="1",
                source_name=NGA_SOURCE_NAME,
                confidence=0.4,
                rights_label=None,
            ),
        ),
        (
            0.35,
            {
                "title": "The Horse Tamer",
                "artist": "Edgar Degas",
                "medium": "bronze sculpture",
            },
            ArtworkLookupCandidate(
                title="The Horse Tamer",
                artist="Edgar Degas",
                date="1880",
                medium="bronze sculpture",
                image_url=None,
                object_url="https://example.org/sculpture",
                accession_number="2",
                source_name=NGA_SOURCE_NAME,
                confidence=0.35,
                rights_label=None,
            ),
        ),
        (
            0.33,
            {
                "title": "Ballet Rehearsal on Stage",
                "artist": "Edgar Degas",
                "medium": "pastel on paper",
            },
            ArtworkLookupCandidate(
                title="Ballet Rehearsal on Stage",
                artist="Edgar Degas",
                date="c. 1879",
                medium="pastel on paper",
                image_url=None,
                object_url="https://example.org/ballet",
                accession_number="3",
                source_name=NGA_SOURCE_NAME,
                confidence=0.33,
                rights_label=None,
            ),
        ),
    ]

    ranked = rank_lookup_candidates(raw, query, strategy="semantic")
    assert ranked
    assert ranked[0].title == "Ballet Rehearsal on Stage"
    assert ranked[0].title != "Portrait of Henri Valpinçon"


def test_degas_dancer_image_ranks_dance_works_without_exact_title(db_session, monkeypatch) -> None:
    from app.models import Artwork

    visual = VisualAnalysis(
        subject="multiple female figures outdoors",
        composition=["grouped dancers", "cropped figures at edge of frame"],
        medium_clues=["pastel on paper"],
        period_clues=["late 19th century"],
        clothing=["tutus"],
        style_signals=["Impressionist dance scene", "Degas-like pastels"],
        performance_indicators=["ballet rehearsal", "dance performance"],
        visual_tags=["ballet", "dancers", "Degas-like", "pastel"],
    )
    draft = ResearchDraft(
        short_summary="",
        historical_context="",
        visual_elements_to_notice=[],
        related_questions=[],
        visual_hypothesis_title="Four Dancers",
        visual_hypothesis_artist="Edgar Degas",
        visual_analysis=VisualAnalysisRead.model_validate(visual.model_dump()),
    )
    artwork = Artwork(title="Unknown", visit_id=None, image_url="/uploads/1.webp")
    db_session.add(artwork)
    db_session.commit()

    built = build_exact_artwork_lookup_query(
        artwork,
        db_session,
        draft,
        museum_name="National Gallery of Art",
    )
    assert built.query.semantic_search is True
    assert "dancers" in " ".join(built.query.expanded_search_terms).lower()
    assert "ballet" in " ".join(built.query.expanded_search_terms).lower()

    ranked = rank_lookup_candidates(
        [
            (
                0.4,
                {
                    "title": "Portrait of a Man",
                    "artist": "Edgar Degas",
                    "medium": "oil on canvas",
                },
                ArtworkLookupCandidate(
                    title="Portrait of a Man",
                    artist="Edgar Degas",
                    date="1865",
                    medium="oil on canvas",
                    image_url=None,
                    object_url="https://example.org/portrait",
                    accession_number="p1",
                    source_name=NGA_SOURCE_NAME,
                    confidence=0.55,
                    rights_label=None,
                ),
            ),
            (
                0.35,
                {
                    "title": "Ballet Rehearsal",
                    "artist": "Edgar Degas",
                    "medium": "pastel on paper",
                },
                ArtworkLookupCandidate(
                    title="Ballet Rehearsal",
                    artist="Edgar Degas",
                    date="c. 1876",
                    medium="pastel on paper",
                    image_url=None,
                    object_url="https://example.org/ballet",
                    accession_number="d1",
                    source_name=NGA_SOURCE_NAME,
                    confidence=0.5,
                    rights_label=None,
                ),
            ),
            (
                0.33,
                {
                    "title": "Horse and Rider",
                    "artist": "Edgar Degas",
                    "medium": "bronze",
                },
                ArtworkLookupCandidate(
                    title="Horse and Rider",
                    artist="Edgar Degas",
                    date="1880",
                    medium="bronze",
                    image_url=None,
                    object_url="https://example.org/sculpture",
                    accession_number="s1",
                    source_name=NGA_SOURCE_NAME,
                    confidence=0.48,
                    rights_label=None,
                ),
            ),
        ],
        built.query,
        strategy="semantic",
    )
    assert ranked
    assert ranked[0].title == "Ballet Rehearsal"
    assert ranked[0].title != "Portrait of a Man"
    assert ranked.index(next(item for item in ranked if item.title == "Ballet Rehearsal")) < ranked.index(
        next(item for item in ranked if item.title == "Horse and Rider")
    )


def test_exact_artwork_identification_uses_related_work_copy() -> None:
    lookup = ArtworkLookupResponse(
        candidates=[
            ArtworkLookupCandidateRead(
                title="Ballet Rehearsal",
                artist="Edgar Degas",
                date="c. 1876",
                medium="pastel on paper",
                image_url=None,
                object_url="https://example.org/ballet",
                accession_number="d1",
                source_name=NGA_SOURCE_NAME,
                confidence=0.52,
                rights_label=None,
                visual_similarity=0.34,
                identity_certainty=0.48,
                low_confidence=False,
                match_tier="possible",
            )
        ],
        sources_searched=[NGA_SOURCE_NAME],
        query_used="Four Dancers · Edgar Degas · ballet · dancers",
        query_source="visual_keywords",
        query_strategy="semantic",
        search_scope="museum",
        museum_collection_name=NGA_SOURCE_NAME,
        retrieval_intent="exact_artwork",
    )
    visual = VisualAnalysis(
        subject="grouped ballet dancers",
        visual_tags=["ballet", "dancers", "pastel"],
    )
    draft = ResearchDraft(
        short_summary="",
        historical_context="",
        visual_elements_to_notice=[],
        related_questions=[],
        visual_hypothesis_title="Four Dancers",
        visual_hypothesis_artist="Edgar Degas",
        visual_analysis=VisualAnalysisRead.model_validate(visual.model_dump()),
    )

    identification = build_identification(
        draft,
        lookup,
        visual,
        visit_museum_name="National Gallery of Art",
        exact_artwork_search=True,
    )

    assert identification.identification_mode == "possible_match"
    assert "Related NGA works" in identification.display_summary
    assert "Similar Degas works" in identification.display_summary
    assert "exact match" not in identification.display_summary.lower()


def test_staged_lookup_uses_semantic_strategy_for_expanded_query(monkeypatch) -> None:
    query = ArtworkLookupQuery(
        title="Four Dancers",
        artist="Edgar Degas",
        museum_name="National Gallery of Art",
        source="nga",
        has_title_query=True,
        semantic_search=True,
        expanded_search_terms=tuple(
            expand_artwork_search_terms(title="Four Dancers", artist="Edgar Degas")
        ),
    )

    def fake_collect(_query: ArtworkLookupQuery):
        return [
            (
                0.5,
                {"title": "Ballet Rehearsal", "artist": "Edgar Degas", "medium": "pastel"},
                ArtworkLookupCandidate(
                    title="Ballet Rehearsal",
                    artist="Edgar Degas",
                    date="1876",
                    medium="pastel on paper",
                    image_url=None,
                    object_url="https://example.org/1",
                    accession_number="1",
                    source_name=NGA_SOURCE_NAME,
                    confidence=0.5,
                    rights_label=None,
                ),
            )
        ]

    monkeypatch.setattr("app.services.lookup_stages.collect_nga_scored_candidates", fake_collect)
    result = lookup_artwork_candidates_staged(query)
    assert result.query_strategy == "semantic"
    assert result.candidates or result.related_candidates
