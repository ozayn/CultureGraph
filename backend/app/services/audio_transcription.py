"""Transcribe audio notes via OpenAI Whisper."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.config import settings
from app.services.audio_language import AudioNoteLanguage, refine_detected_language

logger = logging.getLogger(__name__)

TRANSCRIPTION_UNAVAILABLE = (
    "Transcription is unavailable. Add OPENAI_API_KEY or enter a transcript manually."
)


class TranscriptionError(RuntimeError):
    """Raised when transcription cannot be completed."""


@dataclass(frozen=True)
class TranscriptionResult:
    transcript_original: str
    detected_language: AudioNoteLanguage
    transcript_english: str | None = None


class AudioTranscriptionProvider(Protocol):
    async def transcribe_file(self, path: Path, *, filename: str) -> TranscriptionResult: ...


class PlaceholderTranscriptionProvider:
    async def transcribe_file(self, path: Path, *, filename: str) -> TranscriptionResult:
        raise TranscriptionError(TRANSCRIPTION_UNAVAILABLE)


class OpenAITranscriptionProvider:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key.strip()

    async def transcribe_file(self, path: Path, *, filename: str) -> TranscriptionResult:
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
                    response_format="verbose_json",
                )
        except Exception as exc:
            logger.warning("Audio transcription failed: %s", exc)
            raise TranscriptionError("Could not transcribe audio. Try again or enter text manually.") from exc

        text = (response.text or "").strip()
        if not text:
            raise TranscriptionError("Transcription returned empty text.")

        whisper_language = getattr(response, "language", None)
        detected = refine_detected_language(text, whisper_language)
        english: str | None = None
        if detected in {"fa", "mixed"}:
            english = await self._translate_audio_to_english(client, path, filename=filename)

        return TranscriptionResult(
            transcript_original=text,
            detected_language=detected,
            transcript_english=english,
        )

    async def _translate_audio_to_english(self, client, path: Path, *, filename: str) -> str | None:
        try:
            with path.open("rb") as handle:
                response = await client.audio.translations.create(
                    model=settings.openai_transcription_model,
                    file=(filename, handle),
                )
        except Exception as exc:
            logger.warning("Audio English translation failed: %s", exc)
            return None
        translated = (response.text or "").strip()
        return translated or None


def transcribe_manual_text(transcript: str) -> TranscriptionResult:
    original = transcript.strip()
    if not original:
        raise TranscriptionError("Transcript is empty.")
    detected: AudioNoteLanguage = refine_detected_language(original)
    english: str | None = None
    if detected == "en":
        english = None
    # English companion left empty for manual Farsi/mixed — interpretation handles English output.
    return TranscriptionResult(
        transcript_original=original,
        detected_language=detected,
        transcript_english=english,
    )


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
