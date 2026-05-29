"""Transcribe audio notes via OpenAI Whisper."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol

from app.config import settings

logger = logging.getLogger(__name__)

TRANSCRIPTION_UNAVAILABLE = (
    "Transcription is unavailable. Add OPENAI_API_KEY or enter a transcript manually."
)


class TranscriptionError(RuntimeError):
    """Raised when transcription cannot be completed."""


class AudioTranscriptionProvider(Protocol):
    async def transcribe_file(self, path: Path, *, filename: str) -> str: ...


class PlaceholderTranscriptionProvider:
    async def transcribe_file(self, path: Path, *, filename: str) -> str:
        raise TranscriptionError(TRANSCRIPTION_UNAVAILABLE)


class OpenAITranscriptionProvider:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key.strip()

    async def transcribe_file(self, path: Path, *, filename: str) -> str:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise TranscriptionError(
                "OpenAI client is not installed. Run pip install openai."
            ) from exc

        client = AsyncOpenAI(api_key=self._api_key)
        try:
            with path.open("rb") as handle:
                response = await client.audio.transcriptions.create(
                    model=settings.openai_transcription_model,
                    file=(filename, handle),
                )
        except Exception as exc:
            logger.warning("Audio transcription failed: %s", exc)
            raise TranscriptionError("Could not transcribe audio. Try again or enter text manually.") from exc

        text = (response.text or "").strip()
        if not text:
            raise TranscriptionError("Transcription returned empty text.")
        return text


def get_transcription_provider() -> AudioTranscriptionProvider:
    api_key = settings.openai_api_key
    if api_key and api_key.strip():
        return OpenAITranscriptionProvider(api_key)
    return PlaceholderTranscriptionProvider()


def resolve_audio_file_path(audio_url: str) -> Path:
    relative = audio_url.removeprefix("/uploads/").lstrip("/")
    path = (Path(settings.upload_dir).resolve() / relative).resolve()
    if not path.is_file():
        raise TranscriptionError("Audio file is missing on disk.")
    return path
