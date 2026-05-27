"""Tests for retrieval-assisted artwork identification."""

from __future__ import annotations

from app.schemas import ArtworkLookupCandidateRead, ArtworkLookupResponse, ResearchDraft, VisualAnalysisRead
from app.services.artwork_identification import (
    build_identification,
    calibrate_research_draft,
    rerank_candidates_with_visual,
)
from app.services.visual_analysis import VisualAnalysis, collect_visual_keywords


def _candidate(
    title: str,
    *,
    artist: str | None = None,
    confidence: float = 0.5,
    low_confidence: bool = False,
) -> ArtworkLookupCandidateRead:
    return ArtworkLookupCandidateRead(
        title=title,
        artist=artist,
        date="c. 1520",
        medium="oil on panel",
        image_url="https://example.org/image.jpg",
        image_thumbnail_url=None,
        object_url="https://example.org/object",
        accession_number="123",
        source_name="National Gallery of Art",
        confidence=confidence,
        rights_label="CC0",
        external_id="nga-123",
        low_confidence=low_confidence,
        match_reasons=["Title similarity"],
    )


def _draft_with_visual(**overrides) -> ResearchDraft:
    visual = VisualAnalysisRead(
        subject="cardinal in red robes",
        composition=["three-quarter bust portrait"],
        medium_clues=["oil on panel"],
        period_clues=["16th century"],
        clothing=["red cardinal's hat", "ecclesiastical vestments"],
        color_palette=["crimson", "deep brown"],
        notable_objects=["pectoral cross"],
        style_signals=["Roman school", "soft modeling"],
        movement_style="Italian Renaissance ecclesiastical portrait",
    )
    base = {
        "short_summary": "Visual analysis pending catalog verification.",
        "historical_context": "Ecclesiastical portraiture flourished in Renaissance Rome.",
        "visual_elements_to_notice": ["Red vestments", "Direct gaze"],
        "related_questions": ["Which Roman collections hold similar portraits?"],
        "confidence": 0.45,
        "period_or_movement": "Italian Renaissance",
        "visual_analysis": visual,
    }
    base.update(overrides)
    return ResearchDraft(**base)


def test_collect_visual_keywords_deduplicates() -> None:
    visual = VisualAnalysis(
        subject="cardinal portrait",
        style_signals=["Renaissance portrait", "cardinal portrait"],
        movement_style="Italian Renaissance",
    )
    keywords = collect_visual_keywords(visual, period_or_movement="Italian Renaissance")
    assert "cardinal portrait" in keywords
    assert keywords.count("Italian Renaissance") == 1


def test_build_identification_catalog_match_when_verified() -> None:
    draft = _draft_with_visual(
        possible_title="Portrait of a Cardinal",
        possible_artist="Sebastiano del Piombo",
    )
    lookup = ArtworkLookupResponse(
        candidates=[
            _candidate(
                "Portrait of a Cardinal",
                artist="Sebastiano del Piombo",
                confidence=0.96,
            )
        ],
        sources_searched=["National Gallery of Art"],
        query_used="Portrait of a Cardinal · Sebastiano del Piombo",
        query_source="visual_keywords",
    )

    identification = build_identification(draft, lookup)

    assert identification.identification_mode == "catalog_match"
    assert identification.confidence_level in {"high", "medium"}
    assert identification.suggested_title == "Portrait of a Cardinal"
    assert identification.suggested_artist == "Sebastiano del Piombo"
    assert "Verified collection match" in identification.display_summary or "Strong probable match" in identification.display_summary


def test_build_identification_style_subject_without_candidates() -> None:
    draft = _draft_with_visual()
    lookup = ArtworkLookupResponse(
        candidates=[],
        sources_searched=["National Gallery of Art"],
        query_used="Italian Renaissance ecclesiastical portrait",
        query_source="visual_keywords",
        notice="No close matches found.",
    )

    identification = build_identification(draft, lookup)

    assert identification.identification_mode == "style_subject"
    assert identification.confidence_level == "low"
    assert identification.suggested_title is None
    assert identification.suggested_artist is None
    assert "Italian Renaissance ecclesiastical portrait" in identification.display_summary


def test_build_identification_possible_match_not_authoritative() -> None:
    draft = _draft_with_visual()
    lookup = ArtworkLookupResponse(
        candidates=[
            _candidate(
                "Portrait of Cardinal Alessandro Farnese",
                artist="Sebastiano del Piombo",
                confidence=0.61,
                low_confidence=True,
            )
        ],
        sources_searched=["National Gallery of Art"],
        query_used="cardinal in red robes",
        query_source="visual_keywords",
    )

    identification = build_identification(draft, lookup)

    assert identification.identification_mode == "possible_match"
    assert identification.suggested_title is None
    assert identification.suggested_artist is None
    assert identification.confidence_level in {"low", "medium"}


def test_calibrate_research_draft_avoids_hallucinated_title() -> None:
    draft = _draft_with_visual(
        possible_title="Portrait of Cardinal Alessandro Farnese",
        possible_artist="Sebastiano del Piombo",
    )
    lookup = ArtworkLookupResponse(
        candidates=[
            _candidate(
                "Portrait of a Cardinal",
                artist="Workshop of Raphael",
                confidence=0.58,
                low_confidence=True,
            )
        ],
        sources_searched=["National Gallery of Art"],
        query_used="cardinal portrait",
        query_source="visual_keywords",
    )
    identification = build_identification(draft, lookup)
    calibrated = calibrate_research_draft(draft, identification)

    assert calibrated.possible_title != "Portrait of Cardinal Alessandro Farnese"
    assert calibrated.short_summary == identification.display_summary


def test_calibrate_research_draft_applies_catalog_match() -> None:
    draft = _draft_with_visual(
        possible_title="Portrait of Bindo Altoviti",
        possible_artist="Raphael",
    )
    lookup = ArtworkLookupResponse(
        candidates=[
            _candidate(
                "Portrait of Bindo Altoviti",
                artist="Raphael",
                confidence=0.96,
            )
        ],
        sources_searched=["National Gallery of Art"],
        query_used="Portrait of Bindo Altoviti · Raphael",
        query_source="visual_keywords",
    )
    identification = build_identification(draft, lookup)
    calibrated = calibrate_research_draft(draft, identification)

    assert calibrated.possible_title == "Portrait of Bindo Altoviti"
    assert calibrated.possible_artist == "Raphael"


def test_rerank_candidates_boosts_visual_overlap_without_identity_inflation() -> None:
    visual = VisualAnalysis(
        subject="cardinal in red robes",
        style_signals=["ecclesiastical portrait"],
    )
    keywords = collect_visual_keywords(visual, period_or_movement="Italian Renaissance")
    candidates = [
        _candidate("Landscape with River", confidence=0.62),
        _candidate("Portrait of a Cardinal", artist="Unknown", confidence=0.58),
    ]

    reranked = rerank_candidates_with_visual(candidates, visual, keywords)

    assert reranked[0].title == "Portrait of a Cardinal"
    assert (reranked[0].visual_similarity or 0) >= (candidates[1].confidence or 0) * 0.2
    assert (reranked[0].identity_certainty or reranked[0].confidence) <= 0.75
