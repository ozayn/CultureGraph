"""Regression tests for distinctive visual cue extraction and ranking."""

from __future__ import annotations

from app.schemas import ArtworkLookupCandidateRead, ResearchDraft, VisualAnalysisRead
from app.services.artwork_identification import rerank_candidates_with_visual
from app.services.visual_analysis import (
    VisualAnalysis,
    collect_visual_keywords,
    collect_weighted_visual_tags,
    derive_visual_tags,
    visual_tag_ranking_adjustment,
)


def _degas_ballet_visual() -> VisualAnalysis:
    return VisualAnalysis(
        subject="multiple female figures outdoors",
        composition=["grouped dancers", "cropped figures at edge of frame"],
        medium_clues=["pastel on paper"],
        period_clues=["late 19th century"],
        clothing=["tutus"],
        style_signals=["Impressionist dance scene", "Degas-like pastels"],
        movement_style="19th-century Impressionist ballet scene",
        performance_indicators=["ballet rehearsal", "dance performance"],
        costume_clues=["tutus", "ballet costume"],
        posture_gesture=["theatrical gesture", "dance pose"],
        brushwork_technique=["soft layered pastel"],
        framing_cropping=["cropped dancer composition"],
        movement_depiction=["mid-motion dancers"],
        theatrical_indicators=["rehearsal room"],
        visual_tags=["ballet", "dancers", "Degas-like", "pastel", "Impressionist dance scene"],
    )


def _candidate(title: str, *, artist: str | None, medium: str) -> ArtworkLookupCandidateRead:
    return ArtworkLookupCandidateRead(
        title=title,
        artist=artist,
        date="c. 1899",
        medium=medium,
        image_url="https://example.org/image.jpg",
        image_thumbnail_url=None,
        object_url="https://example.org/object",
        accession_number="123",
        source_name="National Gallery of Art",
        confidence=0.62,
        rights_label="CC0",
        external_id=f"nga-{title.lower().replace(' ', '-')}",
        low_confidence=False,
        match_reasons=["Title similarity"],
    )


def test_derive_visual_tags_prefers_distinctive_ballet_cues() -> None:
    tags = derive_visual_tags(_degas_ballet_visual())

    assert "ballet" in tags
    assert "dancers" in tags
    assert "pastel" in tags
    assert "Degas-like" in tags


def test_collect_visual_keywords_prioritizes_tags_over_generic_subject() -> None:
    keywords = collect_visual_keywords(_degas_ballet_visual())

    assert keywords[0] == "ballet"
    assert "multiple female figures outdoors" in keywords
    assert keywords.index("ballet") < keywords.index("multiple female figures outdoors")


def test_ballet_visual_tags_boost_dance_works_and_penalize_bathers() -> None:
    visual = _degas_ballet_visual()
    tags = collect_weighted_visual_tags(visual)

    dance_adj = visual_tag_ranking_adjustment(
        "Four Dancers Edgar Degas pastel on paper",
        tags,
        visual,
    )
    bather_adj = visual_tag_ranking_adjustment(
        "The Large Bathers Paul Cézanne oil on canvas",
        tags,
        visual,
    )

    assert dance_adj > 0.08
    assert bather_adj < -0.08


def test_degas_style_ballet_image_ranks_dance_work_above_cezanne_bathers() -> None:
    visual = _degas_ballet_visual()
    tags = collect_weighted_visual_tags(visual)
    keywords = collect_visual_keywords(visual)
    draft = ResearchDraft(
        short_summary="Visual analysis pending catalog verification.",
        historical_context="Degas returned repeatedly to ballet rehearsal rooms.",
        visual_elements_to_notice=["Grouped dancers"],
        related_questions=["Which museum holds this pastel?"],
        visual_hypothesis_title="Four Dancers",
        visual_hypothesis_artist="Edgar Degas",
        visual_analysis=VisualAnalysisRead.model_validate(visual.model_dump()),
    )

    candidates = [
        _candidate("The Large Bathers", artist="Paul Cézanne", medium="oil on canvas"),
        _candidate("Four Dancers", artist="Edgar Degas", medium="pastel on paper"),
        _candidate("Woman Ironing", artist="Edgar Degas", medium="oil on canvas"),
    ]

    reranked = rerank_candidates_with_visual(
        candidates,
        visual,
        keywords,
        draft=draft,
    )

    assert reranked[0].title == "Four Dancers"
    assert reranked[0].title != "The Large Bathers"
    assert "Distinctive visual tag overlap" in (reranked[0].match_reasons or [])

    bather = next(item for item in reranked if item.title == "The Large Bathers")
    assert "Visual tag mismatch" in (bather.match_reasons or [])
    assert reranked.index(next(item for item in reranked if item.title == "Four Dancers")) < reranked.index(
        bather
    )
