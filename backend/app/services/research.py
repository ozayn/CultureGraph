import json
from typing import Protocol

from app.config import settings
from app.schemas import AiSuggestedAnnotation, ResearchDraft, SuggestedAnnotationPosition


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
        title = artwork_context.get("title", "this artwork")
        artist = artwork_context.get("artist") or "an unknown artist"
        year = artwork_context.get("year_period") or "an unspecified period"

        return ResearchDraft(
            short_summary=(
                f"{title} by {artist} ({year}) is a notable work worth studying "
                "for its cultural and visual significance."
            ),
            historical_context=(
                f"This piece reflects the artistic concerns of {year}. "
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
                f"What historical events surrounded the creation of {title}?",
                "How does this work compare to others by the same artist?",
                "What might contemporary viewers have understood differently?",
            ],
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


def serialize_research_draft(draft: ResearchDraft) -> dict[str, str | None]:
    return {
        "short_summary": draft.short_summary,
        "historical_context": draft.historical_context,
        "visual_elements_to_notice": json.dumps(draft.visual_elements_to_notice),
        "related_questions": json.dumps(draft.related_questions),
        "suggested_annotations": json.dumps(
            [item.model_dump(mode="json") for item in draft.suggested_annotations]
        ),
        "possible_title": draft.possible_title,
        "possible_artist": draft.possible_artist,
    }


def get_research_provider() -> LLMProvider:
    api_key = settings.anthropic_api_key
    if not api_key or not api_key.strip():
        return MockLLMProvider()

    from app.services.claude_research import ClaudeResearchProvider

    return ClaudeResearchProvider(api_key)
