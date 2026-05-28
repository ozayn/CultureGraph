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
from app.schemas import ClaudeResearchResponse, ResearchDraft, VisualAnalysisRead
from app.services.claude_json import JsonExtractionError, extract_json_object
from app.services.research import ResearchConfigurationError, ResearchProviderError
from app.services.visual_analysis import (
    build_visual_summary,
    extract_artist_from_ocr,
    extract_title_from_ocr,
)

JSON_SCHEMA_PROMPT = """\
Return ONLY a single JSON object (no markdown fences, no commentary) with this exact shape:
{
  "visual_analysis": {
    "subject": string or null,
    "composition": [string, ...],
    "medium_clues": [string, ...],
    "period_clues": [string, ...],
    "clothing": [string, ...],
    "color_palette": [string, ...],
    "notable_objects": [string, ...],
    "style_signals": [string, ...],
    "movement_style": string or null
  },
  "possible_title": string or null,
  "possible_artist": string or null,
  "period_or_movement": string or null,
  "visible_elements": [string, ...],
  "ocr_label_text": string or null,
  "historical_context": string,
  "confidence": number between 0 and 1,
  "suggested_annotations": [
    {
      "category": "observation" | "symbol" | "history" | "question" | "composition" | "material",
      "note": string,
      "tags": [string, ...],
      "linked_concept_names": [string, ...],
      "confidence": number between 0 and 1,
      "suggested_position": {
        "x_percent": number or null,
        "y_percent": number or null,
        "reason": string or null
      }
    }
  ]
}

Rules:
- Stage 1 is visual extraction. Do NOT treat possible_title or possible_artist as verified catalog facts.
- Set possible_title and possible_artist ONLY when:
  (a) ocr_label_text explicitly names them on a legible wall label, OR
  (b) the image strongly suggests a well-known, visually distinctive work (e.g. a famous ballet scene, iconic composition).
- For (b), use widely recognized titles/artists only when the visual evidence is strong — never for generic portraits or vague scenes.
- Unverified visual hypotheses must keep confidence below 0.55.
- When only style/subject is clear (no plausible famous-work hypothesis), leave possible_title and possible_artist null.
- visual_analysis: describe subject, composition, medium clues, period/style signals, clothing, palette, and notable objects.
- movement_style: broad style label (e.g. "Northern Renaissance ecclesiastical portrait"), not a specific catalog title.
- Base visual analysis on the image when provided; use user metadata as hints, not confirmed facts.
- Read any visible wall labels, captions, or placards into ocr_label_text when legible.
- confidence reflects certainty of visual description only (0=very uncertain, 1=very clear visual read).
- Keep confidence below 0.6 when identification would require catalog verification.
- suggested_annotations: 2–5 specific pin ideas tied to visible details, themes, or historical context.
- tags: short freeform labels (e.g. composition, gesture, colonialism, material).
- linked_concept_names: optional related concepts/movements/themes as plain strings.
- suggested_position.x_percent and suggested_position.y_percent must BOTH be null unless you can
  confidently locate a region from image analysis. Never invent precise coordinates.
- When coordinates are null, set suggested_position.reason to explain what the viewer should look for.
- If no image is provided or the region is uncertain, keep both coordinates null.
"""


SUPPORTED_IMAGE_SUFFIXES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def claude_response_to_draft(claude: ClaudeResearchResponse) -> ResearchDraft:
    visual = claude.visual_analysis
    title_from_ocr = extract_title_from_ocr(claude.ocr_label_text)
    artist_from_ocr = extract_artist_from_ocr(claude.ocr_label_text)

    hypothesis_title: str | None = None
    hypothesis_artist: str | None = None
    if claude.possible_title and not title_from_ocr:
        cleaned = claude.possible_title.strip()
        hypothesis_title = cleaned or None
    if claude.possible_artist and not artist_from_ocr:
        cleaned = claude.possible_artist.strip()
        hypothesis_artist = cleaned or None

    hypothesis_confidence = None
    hypothesis_source = None
    if hypothesis_title or hypothesis_artist:
        hypothesis_confidence = min(claude.confidence, 0.55)
        hypothesis_source = "vision"

    short_summary = build_visual_summary(
        _to_visual_analysis(visual),
        period_or_movement=claude.period_or_movement,
        vision_confidence=claude.confidence,
    )

    related_questions: list[str] = []
    if claude.ocr_label_text:
        related_questions.append(
            f"What does the visible label text tell us? \"{claude.ocr_label_text}\""
        )
    if hypothesis_title or hypothesis_artist:
        artist_bit = f" by {hypothesis_artist}" if hypothesis_artist else ""
        related_questions.append(
            f"Can we verify the visual hypothesis \"{hypothesis_title or 'Unknown title'}{artist_bit}\" against museum catalogs?"
        )
    if visual and visual.movement_style:
        related_questions.append(
            f"Which museum collections hold similar {visual.movement_style} works?"
        )
    related_questions.extend(
        [
            "Which official catalog records best match the visible subject and style?",
            "What iconographic details should be verified before accepting an attribution?",
            "Does the medium and support match the proposed period?",
        ]
    )

    return ResearchDraft(
        short_summary=short_summary,
        historical_context=claude.historical_context,
        visual_elements_to_notice=claude.visible_elements,
        related_questions=related_questions,
        suggested_annotations=list(claude.suggested_annotations),
        possible_title=title_from_ocr,
        possible_artist=artist_from_ocr,
        visual_hypothesis_title=hypothesis_title,
        visual_hypothesis_artist=hypothesis_artist,
        visual_hypothesis_confidence=hypothesis_confidence,
        hypothesis_source=hypothesis_source,
        period_or_movement=claude.period_or_movement or (visual.movement_style if visual else None),
        ocr_label_text=claude.ocr_label_text,
        confidence=(
            claude.confidence
            if title_from_ocr
            else min(claude.confidence, hypothesis_confidence or 0.55)
        ),
        visual_analysis=visual,
        source="claude",
    )


def _to_visual_analysis(visual: VisualAnalysisRead | None):
    from app.services.visual_analysis import VisualAnalysis

    if not visual:
        return None
    return VisualAnalysis.model_validate(visual.model_dump())


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
        "Artwork metadata supplied by the visitor (treat as unverified hints):",
        f"- Title (user): {artwork_context.get('title') or 'not provided'}",
        f"- Artist (user): {artwork_context.get('artist') or 'unknown'}",
        f"- Year/period (user): {artwork_context.get('year_period') or 'unknown'}",
        f"- Medium (user): {artwork_context.get('medium') or 'unknown'}",
        f"- Museum/gallery (user): {artwork_context.get('museum_gallery') or 'unknown'}",
        f"- Personal notes: {artwork_context.get('personal_notes') or 'none'}",
    ]
    if artwork_context.get("label_ocr_text"):
        lines.append(
            f"- Wall label OCR (high-trust): {artwork_context['label_ocr_text']}"
        )
    if artwork_context.get("label_image_url"):
        lines.append(
            "- A second image shows the museum wall label. Prefer that label image for ocr_label_text."
        )
    lines.extend(["", JSON_SCHEMA_PROMPT])
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
        label_image_url = artwork_context.get("label_image_url")
        label_image_path = _resolve_image_path(label_image_url)

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
            if label_image_path is not None:
                content.append(
                    {
                        "type": "text",
                        "text": "Image 1 above: the artwork. The next image is the museum wall label.",
                    }
                )

        if label_image_path is not None:
            label_media_type, label_data = _encode_image(label_image_path)
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": label_media_type,
                        "data": label_data,
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
