"""Extract text from museum wall label photos."""

from __future__ import annotations

import base64
import io
import logging

from anthropic import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncAnthropic,
    AuthenticationError,
    RateLimitError,
)
from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import settings

logger = logging.getLogger(__name__)

LABEL_OCR_PROMPT = """\
Transcribe all legible text from this museum wall label or artwork information card.
Return ONLY the raw label text, preserving line breaks.
Do not summarize, interpret, or add commentary.
If no text is legible, return an empty string.
"""


def _normalize_image_bytes(data: bytes) -> tuple[str, str]:
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except UnidentifiedImageError as exc:
        raise ValueError("Could not read label image.") from exc

    image = ImageOps.exif_transpose(image)
    if image.mode not in {"RGB", "L"}:
        image = image.convert("RGB")

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90, optimize=True)
    encoded = base64.standard_b64encode(buffer.getvalue()).decode("ascii")
    return "image/jpeg", encoded


class PlaceholderLabelOcrProvider:
    """No-op OCR provider when vision OCR is unavailable."""

    async def extract_text(self, data: bytes, *, filename: str | None, content_type: str | None) -> str | None:
        return None


class ClaudeLabelOcrProvider:
    def __init__(self, api_key: str) -> None:
        self._client = AsyncAnthropic(
            api_key=api_key.strip(),
            timeout=settings.anthropic_timeout_seconds,
            max_retries=0,
        )

    async def extract_text(self, data: bytes, *, filename: str | None, content_type: str | None) -> str | None:
        try:
            media_type, encoded = _normalize_image_bytes(data)
        except ValueError:
            return None

        try:
            message = await self._client.messages.create(
                model=settings.anthropic_model,
                max_tokens=1024,
                temperature=0,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": encoded,
                                },
                            },
                            {"type": "text", "text": LABEL_OCR_PROMPT},
                        ],
                    }
                ],
            )
        except (AuthenticationError, APITimeoutError, RateLimitError, APIConnectionError, APIStatusError) as exc:
            logger.warning("Label OCR request failed: %s", exc)
            return None

        text_blocks = [
            block.text for block in message.content if getattr(block, "type", None) == "text"
        ]
        if not text_blocks:
            return None

        text = text_blocks[0].strip()
        return text or None


def get_label_ocr_provider() -> PlaceholderLabelOcrProvider | ClaudeLabelOcrProvider:
    api_key = settings.anthropic_api_key
    if api_key and api_key.strip():
        return ClaudeLabelOcrProvider(api_key)
    return PlaceholderLabelOcrProvider()


async def extract_label_ocr_text(
    data: bytes,
    *,
    filename: str | None = None,
    content_type: str | None = None,
) -> str | None:
    provider = get_label_ocr_provider()
    return await provider.extract_text(data, filename=filename, content_type=content_type)
