import json
from typing import Protocol

from app.config import settings
from app.schemas import AiSuggestedAnnotation, ResearchDraft, SuggestedAnnotationPosition, VisualAnalysisRead
from app.services.suggested_annotations import ensure_pending_defaults
from app.services.visual_analysis import VisualAnalysis, build_visual_summary


class ResearchConfigurationError(Exception):
    """Raised when Anthropic is misconfigured (invalid or empty API key)."""


class ResearchProviderError(Exception):
    """Raised when the research provider fails at runtime."""


class LLMProvider(Protocol):
    async def generate_research(self, artwork_context: dict) -> ResearchDraft:
        """Generate research draft from artwork metadata and optional image."""
        ...


class MockLLMProvider:
    async def generate_research(self, artwork_context: dict) -> ResearchDraft:
        title = artwork_context.get("title")
        artist = artwork_context.get("artist")
        year = artwork_context.get("year_period") or "an unspecified period"
        has_user_title = bool(title and str(title).strip() and str(title) != "this artwork")

        visual = VisualAnalysis(
            subject="central figure in formal dress" if not has_user_title else f"depicted subject related to {title}",
            composition=["centered figure", "neutral background"],
            medium_clues=["oil on canvas"],
            period_clues=[year] if year != "an unspecified period" else ["19th century"],
            clothing=["formal attire"],
            color_palette=["earth tones"],
            notable_objects=["architectural backdrop"],
            style_signals=["academic portraiture"],
            movement_style="19th-century portrait tradition",
        )

        short_summary = build_visual_summary(
            visual,
            period_or_movement=year if year != "an unspecified period" else visual.movement_style,
            vision_confidence=0.42,
        )

        return ResearchDraft(
            short_summary=short_summary,
            historical_context=(
                f"This piece reflects artistic concerns of its period. "
                "Consider how patronage, geography, and contemporary events "
                "may have shaped its creation and reception."
            ),
            visual_elements_to_notice=[
                "Composition and focal points",
                "Use of light and shadow",
                "Symbolism in depicted objects or gestures",
                "Material technique and surface texture",
            ],
            related_questions=[
                "Which museum catalog records match the visible subject and style?",
                "How does this work compare to others from the same period?",
                "What might contemporary viewers have understood differently?",
            ],
            possible_title=title if has_user_title else None,
            possible_artist=artist if artist and artist != "an unknown artist" else None,
            period_or_movement=year if year != "an unspecified period" else visual.movement_style,
            confidence=0.42,
            visual_analysis=VisualAnalysisRead.model_validate(visual.model_dump()),
            suggested_annotations=[
                AiSuggestedAnnotation(
                    category="composition",
                    note="Note the central axis and how the eye is guided through the scene.",
                    tags=["composition", "gesture"],
                    linked_concept_names=["American identity"],
                    confidence=0.72,
                    suggested_position=SuggestedAnnotationPosition(
                        x_percent=None,
                        y_percent=None,
                        reason="Place on the main focal area where sight lines converge.",
                    ),
                ),
                AiSuggestedAnnotation(
                    category="symbol",
                    note="Identify recurring motifs that may carry allegorical meaning.",
                    tags=["symbol"],
                    linked_concept_names=["migration"],
                    confidence=0.68,
                    suggested_position=SuggestedAnnotationPosition(
                        x_percent=42.0,
                        y_percent=38.0,
                        reason="Mock provider example pin near the upper-center motif.",
                    ),
                ),
                AiSuggestedAnnotation(
                    category="history",
                    note="Research the patron or institution associated with this work.",
                    tags=["colonialism", "labor"],
                    linked_concept_names=["Manifest Destiny"],
                    confidence=0.61,
                    suggested_position=SuggestedAnnotationPosition(
                        x_percent=None,
                        y_percent=None,
                        reason="Historical context applies to the whole composition.",
                    ),
                ),
            ],
            source="mock",
        )


def serialize_research_draft(draft: ResearchDraft) -> dict[str, str | None | float]:
    visual_payload: str | None = None
    if draft.visual_analysis:
        visual_payload = json.dumps(draft.visual_analysis.model_dump(mode="json"))

    return {
        "short_summary": draft.short_summary,
        "historical_context": draft.historical_context,
        "visual_elements_to_notice": json.dumps(draft.visual_elements_to_notice),
        "related_questions": json.dumps(draft.related_questions),
        "suggested_annotations": json.dumps(
            [
                item.model_dump(mode="json")
                for item in ensure_pending_defaults(draft.suggested_annotations)
            ]
        ),
        "possible_title": draft.possible_title,
        "possible_artist": draft.possible_artist,
        "period_or_movement": draft.period_or_movement,
        "ocr_label_text": draft.ocr_label_text,
        "confidence": draft.confidence,
        "visual_analysis": visual_payload,
    }


def get_research_provider() -> LLMProvider:
    api_key = settings.anthropic_api_key
    if not api_key or not api_key.strip():
        return MockLLMProvider()

    from app.services.claude_research import ClaudeResearchProvider

    return ClaudeResearchProvider(api_key)
