"""Exact artwork retrieval mode — visual keyword search and identification copy."""

from __future__ import annotations

from app.schemas import ArtworkLookupCandidateRead, ArtworkLookupResponse, ResearchDraft, VisualAnalysisRead
from app.services.artwork_identification import build_identification
from app.services.lookup_query import build_exact_artwork_lookup_query
from app.services.visual_analysis import VisualAnalysis, collect_exact_artwork_keywords
from app.sources.museums import NGA_SOURCE_NAME


def test_collect_exact_artwork_keywords_includes_portrait_and_period_cues() -> None:
    visual = VisualAnalysis(
        subject="Portrait of a young man in a red garment",
        clothing=["red doublet", "white collar"],
        color_palette=["crimson", "rose"],
        period_clues=["Renaissance", "Italian"],
        medium_clues=["oil on panel"],
        style_signals=["Northern Renaissance"],
        visual_tags=["portrait", "young man"],
    )

    keywords = collect_exact_artwork_keywords(visual, period_or_movement="Renaissance")

    blob = " ".join(keywords).lower()
    assert "portrait" in blob
    assert "young man" in blob
    assert "red" in blob or "crimson" in blob
    assert "renaissance" in blob
    assert "oil" in blob


def test_build_exact_artwork_lookup_query_uses_visual_keywords_not_title(db_session) -> None:
    from app.models import Artwork

    artwork = Artwork(title="Unknown", visit_id=None, image_url="/uploads/1.webp")
    db_session.add(artwork)
    db_session.commit()

    visual = VisualAnalysis(
        subject="Portrait of a young man",
        medium_clues=["oil painting"],
        period_clues=["Renaissance"],
    )
    draft = ResearchDraft(
        short_summary="",
        historical_context="",
        visual_elements_to_notice=[],
        related_questions=[],
        possible_title="Some Famous Title",
        visual_analysis=VisualAnalysisRead.model_validate(visual.model_dump()),
    )

    built = build_exact_artwork_lookup_query(
        artwork,
        db_session,
        draft,
        museum_name="National Gallery of Art",
    )

    assert built.query_source == "visual_keywords"
    assert built.query.has_title_query is False
    assert "portrait" in built.query_used.lower() or "young man" in built.query_used.lower()


def test_exact_artwork_identification_not_found_copy() -> None:
    lookup = ArtworkLookupResponse(
        candidates=[],
        sources_searched=[NGA_SOURCE_NAME],
        query_used="portrait · young man · Renaissance · oil painting",
        query_source="visual_keywords",
        search_scope="museum",
        museum_collection_name=NGA_SOURCE_NAME,
        retrieval_intent="exact_artwork",
    )
    draft = ResearchDraft(
        short_summary="Renaissance portrait study.",
        historical_context="Italian Renaissance portraiture.",
        visual_elements_to_notice=[],
        related_questions=[],
    )
    visual = VisualAnalysis(subject="Portrait of a young man")

    identification = build_identification(
        draft,
        lookup,
        visual,
        visit_museum_name="National Gallery of Art",
        exact_artwork_search=True,
    )

    assert identification.identification_mode == "exact_not_found"
    assert identification.retrieval_intent == "exact_artwork"
    assert "No close match" in identification.display_summary
    assert "Style resembles" not in identification.display_summary


def test_exact_artwork_identification_possible_candidates_copy() -> None:
    lookup = ArtworkLookupResponse(
        candidates=[
            ArtworkLookupCandidateRead(
                title="Portrait of a Young Man",
                artist="Unknown Italian",
                date="1500",
                medium="oil on panel",
                image_url=None,
                object_url="https://example.com/nga",
                accession_number="1",
                source_name=NGA_SOURCE_NAME,
                confidence=0.52,
                rights_label=None,
                visual_similarity=0.31,
                identity_certainty=0.48,
                low_confidence=False,
                match_tier="possible",
            )
        ],
        sources_searched=[NGA_SOURCE_NAME],
        query_used="portrait · young man · Renaissance",
        query_source="visual_keywords",
        search_scope="museum",
        museum_collection_name=NGA_SOURCE_NAME,
        retrieval_intent="exact_artwork",
    )
    visual = VisualAnalysis(
        subject="Portrait of a young man in red",
        period_clues=["Renaissance"],
    )
    draft = ResearchDraft(
        short_summary="",
        historical_context="",
        visual_elements_to_notice=[],
        related_questions=[],
        visual_hypothesis_title="Portrait of a Young Man",
        visual_hypothesis_artist="Unknown Italian",
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
    assert "Related NGA works" in identification.display_summary or "Similar" in identification.display_summary
    assert identification.retrieval_intent == "exact_artwork"
