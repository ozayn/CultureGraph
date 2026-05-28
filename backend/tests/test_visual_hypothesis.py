"""Regression tests for unverified AI visual hypotheses."""

from __future__ import annotations

from app.schemas import ArtworkLookupCandidateRead, ArtworkLookupResponse, ResearchDraft, VisualAnalysisRead
from app.services.artwork_identification import build_identification, calibrate_research_draft
from app.services.lookup_query import build_retrieval_lookup_query


def _degas_draft() -> ResearchDraft:
    visual = VisualAnalysisRead(
        subject="four ballet dancers in rehearsal",
        composition=["figures grouped across the foreground"],
        medium_clues=["pastel on paper"],
        period_clues=["late 19th century"],
        clothing=["tutus"],
        color_palette=["peach", "green"],
        notable_objects=["barre"],
        style_signals=["Impressionist ballet scene", "Degas-like pastels"],
        movement_style="19th-century Impressionist ballet scene",
    )
    return ResearchDraft(
        short_summary="Visual analysis pending catalog verification.",
        historical_context="Degas returned repeatedly to ballet rehearsal rooms.",
        visual_elements_to_notice=["Grouped dancers", "Pastel handling"],
        related_questions=["Which museum holds this pastel?"],
        visual_hypothesis_title="Four Dancers",
        visual_hypothesis_artist="Edgar Degas",
        visual_hypothesis_confidence=0.52,
        hypothesis_source="vision",
        confidence=0.52,
        period_or_movement="Impressionism, c. 1890",
        visual_analysis=visual,
    )


def _candidate(title: str, *, artist: str | None = None, confidence: float = 0.5) -> ArtworkLookupCandidateRead:
    return ArtworkLookupCandidateRead(
        title=title,
        artist=artist,
        date="c. 1899",
        medium="pastel on paper",
        image_url="https://example.org/image.jpg",
        image_thumbnail_url=None,
        object_url="https://example.org/object",
        accession_number="123",
        source_name="National Gallery of Art",
        confidence=confidence,
        rights_label="CC0",
        external_id="nga-123",
        low_confidence=confidence < 0.8,
        match_reasons=["Title similarity"],
    )


class _ArtworkStub:
    title = None
    artist = None
    year_period = None
    medium = None
    personal_notes = None


def test_degas_like_image_preserves_visual_hypothesis_after_calibration() -> None:
    draft = _degas_draft()
    lookup = ArtworkLookupResponse(
        candidates=[],
        sources_searched=["National Gallery of Art"],
        query_used="Four Dancers · Edgar Degas",
        query_source="ai_title",
    )

    identification = build_identification(draft, lookup)
    calibrated = calibrate_research_draft(draft, identification)

    assert calibrated.visual_hypothesis_title == "Four Dancers"
    assert calibrated.visual_hypothesis_artist == "Edgar Degas"
    assert calibrated.hypothesis_source == "vision"
    assert "AI visual hypothesis" in identification.display_summary
    assert "Not verified against collection records" in identification.display_summary
    assert calibrated.possible_title is None
    assert calibrated.possible_artist is None


def test_unverified_hypothesis_is_not_high_confidence_catalog_match() -> None:
    draft = _degas_draft()
    lookup = ArtworkLookupResponse(
        candidates=[
            _candidate("Four Dancers", artist="Edgar Degas", confidence=0.58),
        ],
        sources_searched=["National Gallery of Art"],
        query_used="Four Dancers · Edgar Degas",
        query_source="ai_title",
    )

    identification = build_identification(draft, lookup)

    assert identification.identification_mode != "catalog_match"
    assert identification.confidence_level != "high"
    assert identification.suggested_title is None
    assert identification.suggested_artist is None
    assert identification.visual_hypothesis_title == "Four Dancers"


def test_unverified_hypothesis_preserved_in_possible_match_mode() -> None:
    draft = _degas_draft()
    lookup = ArtworkLookupResponse(
        candidates=[
            _candidate("Four Dancers", artist="Edgar Degas", confidence=0.58),
        ],
        sources_searched=["National Gallery of Art"],
        query_used="Four Dancers · Edgar Degas",
        query_source="ai_title",
    )

    identification = build_identification(draft, lookup)

    assert identification.identification_mode == "possible_match"
    assert identification.visual_hypothesis_title == "Four Dancers"
    assert identification.visual_hypothesis_artist == "Edgar Degas"
    assert identification.suggested_title is None


def test_catalog_match_takes_priority_over_visual_hypothesis() -> None:
    draft = _degas_draft()
    lookup = ArtworkLookupResponse(
        candidates=[
            _candidate(
                "Four Dancers",
                artist="Edgar Degas",
                confidence=0.97,
            )
        ],
        sources_searched=["National Gallery of Art"],
        query_used="Four Dancers · Edgar Degas",
        query_source="ai_title",
    )

    identification = build_identification(
        draft.model_copy(update={"ocr_label_text": 'Four Dancers\nEdgar Degas'}),
        lookup,
    )

    assert identification.identification_mode == "catalog_match"
    assert identification.suggested_title == "Four Dancers"
    assert identification.suggested_artist == "Edgar Degas"
    assert identification.visual_hypothesis_title is None


def test_style_only_fallback_when_no_plausible_hypothesis() -> None:
    visual = VisualAnalysisRead(
        subject="formal portrait of an unidentified sitter",
        style_signals=["academic portraiture"],
        movement_style="19th-century Academic or Romantic painting",
    )
    draft = ResearchDraft(
        short_summary="Visual analysis pending catalog verification.",
        historical_context="Academic portraiture emphasized likeness and decorum.",
        visual_elements_to_notice=["Neutral background"],
        related_questions=["Which collections hold similar portraits?"],
        period_or_movement="19th-century Academic or Romantic painting",
        visual_analysis=visual,
    )
    lookup = ArtworkLookupResponse(
        candidates=[],
        sources_searched=["National Gallery of Art"],
        query_used="19th-century Academic or Romantic painting",
        query_source="visual_keywords",
    )

    identification = build_identification(draft, lookup)

    assert identification.identification_mode == "style_subject"
    assert identification.visual_hypothesis_title is None
    assert "AI visual hypothesis" not in identification.display_summary
    assert "Academic or Romantic" in identification.display_summary


def test_retrieval_lookup_uses_visual_hypothesis_title() -> None:
    draft = _degas_draft()
    built = build_retrieval_lookup_query(_ArtworkStub(), None, draft, museum_name=None)  # type: ignore[arg-type]

    assert built.query_source == "ai_title"
    assert built.query_used == "Four Dancers · Edgar Degas"
