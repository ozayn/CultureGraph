"""Turn audio note transcripts into structured CultureGraph observations."""

from __future__ import annotations

import logging
from typing import Any

from anthropic import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncAnthropic,
    AuthenticationError,
    RateLimitError,
)
from pydantic import BaseModel, Field, ValidationError

from app.config import settings
from app.schemas import AiSuggestedAnnotation, AnnotationCategory
from app.services.audio_language import AudioNoteLanguage, language_label
from app.services.claude_json import extract_json_object, sanitize_response_preview

logger = logging.getLogger(__name__)

INTERPRETATION_PROMPT = """\
You help museum visitors turn spoken gallery notes into structured observations.

The user may speak in English, Persian/Farsi, or a mix. Preserve meaning. Do not over-translate \
cultural terms. Return structured JSON in English unless otherwise requested.

Given a voice transcript (and optional artwork/visit context), return ONLY one JSON object:

{
  "cleaned_note": "polished first-person note in English, 1-3 sentences",
  "cleaned_note_original_language": "optional polished note in the speaker's language when not English-only",
  "observations": ["short observation bullets in English"],
  "visual_elements": ["visual details noticed in English"],
  "questions": ["open questions for later research in English"],
  "tags": ["short lowercase English tags for search"],
  "tag_aliases": ["important Farsi/Persian terms or transliterations to keep as search aliases"],
  "suggested_annotations": [
    {
      "category": "observation|symbol|history|composition|material|question",
      "note": "annotation text in English",
      "tags": ["tag"],
      "linked_concept_names": ["concept"]
    }
  ],
  "related_entities": ["artist, movement, or theme names in English when possible"]
}

Rules:
- Preserve the visitor's intent; do not invent facts not supported by the transcript.
- If the transcript is Farsi or mixed, interpret it correctly and write structured fields in English.
- Keep English tags concise. Add Farsi terms to tag_aliases when they are culturally important.
- Do not over-translate proper nouns or art-historical terms; keep them recognizable.
- suggested_annotations should be actionable museum-note bullets, not full essays.
- cleaned_note_original_language is optional; include it for Farsi or mixed notes when helpful.
- If context is missing, stay general and mark uncertainty in observations.
"""


class AudioInterpretationError(RuntimeError):
    """Raised when interpretation cannot be completed."""


class AudioInterpretationDraft(BaseModel):
    cleaned_note: str = Field(min_length=1)
    cleaned_note_original_language: str | None = None
    observations: list[str] = Field(default_factory=list)
    visual_elements: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    tag_aliases: list[str] = Field(default_factory=list)
    suggested_annotations: list[AiSuggestedAnnotation] = Field(default_factory=list)
    related_entities: list[str] = Field(default_factory=list)


class PlaceholderInterpretationProvider:
    async def interpret(
        self,
        *,
        transcript: str,
        context: dict[str, Any],
        detected_language: AudioNoteLanguage = "unknown",
        transcript_english: str | None = None,
    ) -> AudioInterpretationDraft:
        cleaned = (transcript_english or transcript).strip()
        if not cleaned:
            raise AudioInterpretationError("Transcript is empty.")
        original_language_note = transcript.strip() if detected_language in {"fa", "mixed"} else None
        return AudioInterpretationDraft(
            cleaned_note=cleaned,
            cleaned_note_original_language=original_language_note,
            observations=[cleaned],
            tags=[],
            tag_aliases=[],
            suggested_annotations=[],
            related_entities=[],
        )


class ClaudeInterpretationProvider:
    def __init__(self, api_key: str) -> None:
        self._client = AsyncAnthropic(
            api_key=api_key.strip(),
            timeout=settings.anthropic_timeout_seconds,
            max_retries=0,
        )

    async def interpret(
        self,
        *,
        transcript: str,
        context: dict[str, Any],
        detected_language: AudioNoteLanguage = "unknown",
        transcript_english: str | None = None,
    ) -> AudioInterpretationDraft:
        context_lines = [
            f"Artwork title: {context.get('title') or 'Unknown'}",
            f"Artist: {context.get('artist') or 'Unknown'}",
            f"Museum visit: {context.get('museum_name') or 'Unknown'}",
            f"Gallery note context: {context.get('museum_gallery') or ''}",
            f"Detected spoken language: {language_label(detected_language)}",
        ]
        transcript_block = f"Original transcript:\n{transcript.strip()}"
        if transcript_english and transcript_english.strip() != transcript.strip():
            transcript_block += f"\n\nEnglish companion transcript:\n{transcript_english.strip()}"

        user_prompt = "\n".join(context_lines) + "\n\n" + transcript_block

        try:
            message = await self._client.messages.create(
                model=settings.anthropic_model,
                max_tokens=settings.anthropic_max_tokens,
                temperature=0.2,
                messages=[
                    {"role": "user", "content": INTERPRETATION_PROMPT + "\n\n" + user_prompt}
                ],
            )
        except (
            AuthenticationError,
            APITimeoutError,
            RateLimitError,
            APIConnectionError,
            APIStatusError,
        ) as exc:
            logger.warning("Audio interpretation failed: %s", exc)
            raise AudioInterpretationError("Could not interpret transcript.") from exc

        text_blocks = [
            block.text for block in message.content if getattr(block, "type", None) == "text"
        ]
        if not text_blocks:
            raise AudioInterpretationError("Interpretation returned empty text.")

        try:
            payload = extract_json_object(text_blocks[0])
            return AudioInterpretationDraft.model_validate(payload)
        except (ValidationError, ValueError) as exc:
            preview = sanitize_response_preview(text_blocks[0])
            logger.warning("Invalid interpretation JSON: %s", preview)
            raise AudioInterpretationError("Interpretation returned an unexpected shape.") from exc


def get_interpretation_provider() -> PlaceholderInterpretationProvider | ClaudeInterpretationProvider:
    api_key = settings.anthropic_api_key
    if api_key and api_key.strip():
        return ClaudeInterpretationProvider(api_key)
    return PlaceholderInterpretationProvider()


def build_interpretation_context(
    *,
    artwork_title: str | None = None,
    artwork_artist: str | None = None,
    museum_name: str | None = None,
    museum_gallery: str | None = None,
    visit_notes: str | None = None,
) -> dict[str, Any]:
    return {
        "title": artwork_title,
        "artist": artwork_artist,
        "museum_name": museum_name,
        "museum_gallery": museum_gallery,
        "visit_notes": visit_notes,
    }
