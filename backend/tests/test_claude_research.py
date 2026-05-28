"""Tests for Claude vision response mapping."""

from __future__ import annotations

from app.schemas import ClaudeResearchResponse, VisualAnalysisRead
from app.services.claude_research import JSON_SCHEMA_PROMPT, claude_response_to_draft


def test_prompt_allows_plausible_hypotheses_without_famous_work_requirement() -> None:
    assert "does not need to be world-famous" in JSON_SCHEMA_PROMPT
    assert "plausible specific work or attribution" in JSON_SCHEMA_PROMPT
    assert "Unverified visual hypotheses must keep confidence below 0.55" in JSON_SCHEMA_PROMPT


def test_plausible_hypothesis_is_mapped_unverified_with_capped_confidence() -> None:
    visual = VisualAnalysisRead(
        subject="young man in three-quarter pose",
        composition=["figure centered against neutral background"],
        medium_clues=["oil on panel"],
        period_clues=["early 16th century"],
        style_signals=["High Renaissance portrait", "sfumato handling"],
        movement_style="Italian High Renaissance portraiture",
    )
    claude = ClaudeResearchResponse(
        visual_analysis=visual,
        possible_title="Portrait of a Young Man",
        possible_artist="Raphael",
        visual_hypothesis_reason="Three-quarter pose and sfumato handling match Raphael workshop portraits.",
        period_or_movement="High Renaissance, c. 1505",
        visible_elements=["Young sitter", "Neutral background"],
        ocr_label_text=None,
        historical_context="Renaissance portraiture emphasized likeness and decorum.",
        confidence=0.78,
        suggested_annotations=[],
    )

    draft = claude_response_to_draft(claude)

    assert draft.possible_title is None
    assert draft.possible_artist is None
    assert draft.visual_hypothesis_title == "Portrait of a Young Man"
    assert draft.visual_hypothesis_artist == "Raphael"
    assert draft.hypothesis_source == "vision"
    assert draft.visual_hypothesis_confidence is not None
    assert draft.visual_hypothesis_confidence <= 0.55
    assert draft.confidence <= 0.55
