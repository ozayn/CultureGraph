import base64
from pathlib import Path

from anthropic import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncAnthropic,
    AuthenticationError,
    RateLimitError,
)
from pydantic import ValidationError

from app.config import settings
from app.schemas import ClaudeResearchResponse, ResearchDraft
from app.services.claude_json import JsonExtractionError, extract_json_object
from app.services.research import ResearchConfigurationError, ResearchProviderError

JSON_SCHEMA_PROMPT = """\
Return ONLY a single JSON object (no markdown fences, no commentary) with this exact shape:
{
  "possible_title": string or null,
  "possible_artist": string or null,
  "period_or_movement": string or null,
  "visible_elements": [string, ...],
  "ocr_label_text": string or null,
  "historical_context": string,
  "confidence": number between 0 and 1,
  "suggested_annotations": [
    {"category": "observation" | "symbol" | "history" | "question" | "composition", "text": string}
  ]
}

Rules:
- Base visual analysis on the image when provided; use metadata as hints, not facts.
- Read any visible wall labels, captions, or placards into ocr_label_text when legible.
- confidence reflects how certain you are about identification (0=guess, 1=very confident).
- suggested_annotations: 2–5 specific, tappable pin ideas tied to visible details.
- If uncertain about title/artist, set those fields to null and lower confidence.
"""


SUPPORTED_IMAGE_SUFFIXES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def claude_response_to_draft(claude: ClaudeResearchResponse) -> ResearchDraft:
    title = claude.possible_title or "Unidentified artwork"
    artist = claude.possible_artist or "Unknown artist"
    period = claude.period_or_movement or "Unknown period"
    confidence_pct = f"{round(claude.confidence * 100)}%"

    short_summary = (
        f"{title} — possibly by {artist} ({period}). "
        f"Analysis confidence: {confidence_pct}."
    )

    related_questions: list[str] = []
    if claude.ocr_label_text:
        related_questions.append(
            f"What does the visible label text tell us? \"{claude.ocr_label_text}\""
        )
    related_questions.extend(
        [
            f"How does {title} relate to {period}?",
            "What should you verify in the museum catalog or collection database?",
            "Which visible details support or contradict the proposed attribution?",
        ]
    )

    return ResearchDraft(
        short_summary=short_summary,
        historical_context=claude.historical_context,
        visual_elements_to_notice=claude.visible_elements,
        related_questions=related_questions,
        suggested_annotations=[
            {"category": item.category, "text": item.text}
            for item in claude.suggested_annotations
        ],
        possible_title=claude.possible_title,
        possible_artist=claude.possible_artist,
        period_or_movement=claude.period_or_movement,
        ocr_label_text=claude.ocr_label_text,
        confidence=claude.confidence,
        source="claude",
    )


def _resolve_image_path(image_url: str | None) -> Path | None:
    if not image_url:
        return None

    relative = image_url.removeprefix("/uploads/").lstrip("/")
    if not relative or relative == image_url:
        return None

    upload_root = Path(settings.upload_dir).resolve()
    candidate = (upload_root / relative).resolve()

    if upload_root not in candidate.parents and candidate != upload_root:
        return None
    if not candidate.is_file():
        return None

    return candidate


def _encode_image(image_path: Path) -> tuple[str, str]:
    media_type = SUPPORTED_IMAGE_SUFFIXES.get(image_path.suffix.lower())
    if not media_type:
        raise ResearchProviderError(
            f"Unsupported artwork image type '{image_path.suffix}'. "
            "Use JPEG, PNG, GIF, or WebP."
        )

    data = base64.standard_b64encode(image_path.read_bytes()).decode("ascii")
    return media_type, data


def _build_metadata_prompt(artwork_context: dict) -> str:
    lines = [
        "Artwork metadata supplied by the visitor:",
        f"- Title (user): {artwork_context.get('title') or 'unknown'}",
        f"- Artist (user): {artwork_context.get('artist') or 'unknown'}",
        f"- Year/period (user): {artwork_context.get('year_period') or 'unknown'}",
        f"- Medium (user): {artwork_context.get('medium') or 'unknown'}",
        f"- Museum/gallery (user): {artwork_context.get('museum_gallery') or 'unknown'}",
        f"- Personal notes: {artwork_context.get('personal_notes') or 'none'}",
        "",
        JSON_SCHEMA_PROMPT,
    ]
    return "\n".join(lines)


def _extract_json(text: str) -> dict:
    try:
        return extract_json_object(text)
    except JsonExtractionError as exc:
        raise ResearchProviderError(str(exc)) from exc


class ClaudeResearchProvider:
    def __init__(self, api_key: str) -> None:
        if not api_key.strip():
            raise ResearchConfigurationError(
                "ANTHROPIC_API_KEY is set but empty. Add a valid key or remove it to use mock research."
            )

        self._client = AsyncAnthropic(
            api_key=api_key.strip(),
            timeout=settings.anthropic_timeout_seconds,
            max_retries=0,
        )

    async def generate_research(self, artwork_context: dict) -> ResearchDraft:
        image_url = artwork_context.get("image_url")
        image_path = _resolve_image_path(image_url)

        content: list[dict] = []
        if image_path is not None:
            media_type, data = _encode_image(image_path)
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": data,
                    },
                }
            )

        content.append({"type": "text", "text": _build_metadata_prompt(artwork_context)})

        try:
            message = await self._client.messages.create(
                model=settings.anthropic_model,
                max_tokens=settings.anthropic_max_tokens,
                temperature=0.2,
                messages=[{"role": "user", "content": content}],
            )
        except AuthenticationError as exc:
            raise ResearchConfigurationError(
                "ANTHROPIC_API_KEY is invalid or unauthorized. Check the key in your environment."
            ) from exc
        except APITimeoutError as exc:
            raise ResearchProviderError(
                f"Claude request timed out after {settings.anthropic_timeout_seconds:g}s."
            ) from exc
        except RateLimitError as exc:
            raise ResearchProviderError(
                "Claude rate limit reached. Wait a moment and try again."
            ) from exc
        except APIConnectionError as exc:
            raise ResearchProviderError(
                "Could not reach the Anthropic API. Check your network connection."
            ) from exc
        except APIStatusError as exc:
            raise ResearchProviderError(
                f"Anthropic API error ({exc.status_code}): {exc.message}"
            ) from exc

        text_blocks = [
            block.text for block in message.content if getattr(block, "type", None) == "text"
        ]
        if not text_blocks:
            raise ResearchProviderError("Claude returned an empty response.")

        try:
            parsed = ClaudeResearchResponse.model_validate(_extract_json(text_blocks[0]))
        except ValidationError as exc:
            raise ResearchProviderError(
                "Claude response did not match the expected research schema."
            ) from exc

        return claude_response_to_draft(parsed)
