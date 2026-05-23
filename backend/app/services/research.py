import json
from typing import Protocol

from app.schemas import ResearchDraft


class LLMProvider(Protocol):
    async def generate_research(self, artwork_context: dict) -> ResearchDraft:
        """Generate research draft from artwork metadata. Swap in a real LLM later."""
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
                {
                    "category": "composition",
                    "text": "Note the central axis and how the eye is guided through the scene.",
                },
                {
                    "category": "symbol",
                    "text": "Identify recurring motifs that may carry allegorical meaning.",
                },
                {
                    "category": "history",
                    "text": "Research the patron or institution associated with this work.",
                },
            ],
        )


def serialize_research_draft(draft: ResearchDraft) -> dict[str, str]:
    return {
        "short_summary": draft.short_summary,
        "historical_context": draft.historical_context,
        "visual_elements_to_notice": json.dumps(draft.visual_elements_to_notice),
        "related_questions": json.dumps(draft.related_questions),
        "suggested_annotations": json.dumps(draft.suggested_annotations),
    }


llm_provider: LLMProvider = MockLLMProvider()
