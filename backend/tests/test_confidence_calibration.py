"""Regression tests for artwork identification confidence calibration."""

from __future__ import annotations

from app.schemas import ArtworkLookupCandidateRead, ArtworkLookupResponse, ResearchDraft, VisualAnalysisRead
from app.services.artwork_identification import build_identification, rerank_candidates_with_visual
from app.services.confidence_calibration import calibrate_candidate_confidence
from app.services.visual_analysis import VisualAnalysis, collect_visual_keywords


def _candidate(
    title: str,
    *,
    artist: str | None = None,
    confidence: float = 0.5,
) -> ArtworkLookupCandidateRead:
    return ArtworkLookupCandidateRead(
        title=title,
        artist=artist,
        date="c. 1900",
        medium="oil on canvas",
        image_url="https://example.org/image.jpg",
        image_thumbnail_url=None,
        object_url="https://example.org/object",
        accession_number="123",
        source_name="National Gallery of Art",
        confidence=confidence,
        rights_label="CC0",
        external_id="nga-123",
        low_confidence=False,
        match_reasons=["Visual keyword overlap"],
    )


def test_generic_portrait_figure_never_reaches_verified_confidence() -> None:
    calibrated = calibrate_candidate_confidence(
        title_score=0.42,
        artist_score=0.51,
        text_score=0.62,
        candidate_title="Figure",
        candidate_artist="Lovry Mina",
        search_title="standing portrait in gold frame",
        search_artist="",
        has_title_query=True,
        match_reasons=["Visual keyword overlap", "Partial title match"],
        visual_subject="standing figure in dark portrait background",
        visual_keywords=["portrait", "gold frame", "dark background"],
        visual_overlap=0.72,
        subject_overlap=0.35,
    )

    assert calibrated.identity_certainty <= 0.55
    assert calibrated.confidence <= 0.55
    assert calibrated.match_tier in {"possible", "weak"}
    assert "visually similar" in calibrated.match_explanation.lower() or "not enough evidence" in calibrated.match_explanation.lower()


def test_no_ninety_eight_percent_without_exact_evidence() -> None:
    calibrated = calibrate_candidate_confidence(
        title_score=0.48,
        artist_score=0.44,
        text_score=0.78,
        candidate_title="Portrait of a Woman",
        candidate_artist="Unknown artist",
        search_title="museum portrait with gold frame",
        search_artist="",
        has_title_query=True,
        match_reasons=["Visual keyword overlap"],
        visual_subject="woman in portrait with ornate frame",
        visual_overlap=0.81,
        subject_overlap=0.40,
    )

    assert calibrated.confidence < 0.95
    assert calibrated.identity_certainty < 0.60


def test_exact_title_and_artist_can_reach_verified_band() -> None:
    calibrated = calibrate_candidate_confidence(
        title_score=0.96,
        artist_score=0.91,
        text_score=0.94,
        candidate_title="The Emperor Napoleon in His Study at the Tuileries",
        candidate_artist="Jacques-Louis David",
        search_title="The Emperor Napoleon in His Study at the Tuileries",
        search_artist="Jacques-Louis David",
        has_title_query=True,
        match_reasons=["Title match", "Artist match"],
    )

    assert calibrated.identity_certainty >= 0.94
    assert calibrated.match_tier == "high"


def test_ocr_supported_match_can_reach_verified_band() -> None:
    calibrated = calibrate_candidate_confidence(
        title_score=0.88,
        artist_score=0.74,
        text_score=0.82,
        candidate_title="Portrait of Bindo Altoviti",
        candidate_artist="Raphael",
        search_title="Renaissance portrait",
        search_artist="",
        has_title_query=True,
        match_reasons=["Partial title match"],
        ocr_label_text='Title: "Portrait of Bindo Altoviti" · Artist: Raphael',
    )

    assert calibrated.identity_certainty >= 0.95
    assert calibrated.evidence.ocr_supported is True


def test_unrelated_portraits_do_not_become_catalog_match() -> None:
    draft = ResearchDraft(
        short_summary="Visual analysis pending.",
        historical_context="Portraiture",
        visual_elements_to_notice=["Dark background"],
        related_questions=[],
        confidence=0.45,
        period_or_movement="19th century",
        visual_analysis=VisualAnalysisRead(
            subject="standing figure in dark portrait background with gold frame",
            composition=["three-quarter standing portrait"],
            style_signals=["academic portrait"],
            movement_style="19th-century portrait",
        ),
    )
    lookup = ArtworkLookupResponse(
        candidates=[_candidate("Figure", artist="Lovry Mina", confidence=0.98)],
        sources_searched=["National Gallery of Art"],
        query_used="19th-century portrait · standing figure",
        query_source="visual_keywords",
    )

    identification = build_identification(draft, lookup)

    assert identification.identification_mode != "catalog_match"
    assert identification.confidence_level != "high"
    assert identification.suggested_title is None
    assert (identification.identity_certainty or 0) < 0.60


def test_rerank_does_not_inflate_identity_with_visual_overlap() -> None:
    visual = VisualAnalysis(
        subject="standing figure in dark portrait background",
        style_signals=["academic portrait", "gold frame"],
    )
    keywords = collect_visual_keywords(visual, period_or_movement="19th century")
    candidates = [_candidate("Figure", artist="Lovry Mina", confidence=0.98)]

    reranked = rerank_candidates_with_visual(candidates, visual, keywords)

    assert reranked[0].identity_certainty is not None
    assert reranked[0].identity_certainty <= 0.55
    assert reranked[0].visual_similarity is not None
    assert reranked[0].visual_similarity >= 0.10
