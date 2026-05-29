"""Detect and classify English / Farsi audio note transcripts."""

from __future__ import annotations

import re
from typing import Literal

AudioNoteLanguage = Literal["en", "fa", "mixed", "unknown"]

_PERSIAN_ARABIC_RE = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]"
)
_LATIN_RE = re.compile(r"[A-Za-z]")


def map_whisper_language(code: str | None) -> AudioNoteLanguage:
    if not code:
        return "unknown"
    normalized = code.strip().lower()
    if normalized in {"en", "english"}:
        return "en"
    if normalized in {"fa", "fas", "persian", "farsi"}:
        return "fa"
    return "unknown"


def detect_transcript_language(text: str) -> AudioNoteLanguage:
    stripped = text.strip()
    if not stripped:
        return "unknown"

    has_persian = bool(_PERSIAN_ARABIC_RE.search(stripped))
    has_latin = bool(_LATIN_RE.search(stripped))
    if has_persian and has_latin:
        return "mixed"
    if has_persian:
        return "fa"
    if has_latin:
        return "en"
    return "unknown"


def refine_detected_language(
    text: str,
    whisper_language: str | None = None,
) -> AudioNoteLanguage:
    heuristic = detect_transcript_language(text)
    whisper = map_whisper_language(whisper_language)

    if heuristic == "mixed":
        return "mixed"
    if heuristic in {"en", "fa"} and whisper in {"en", "fa"} and heuristic != whisper:
        return "mixed"
    if heuristic != "unknown":
        return heuristic
    if whisper != "unknown":
        return whisper
    return "unknown"


def language_label(code: AudioNoteLanguage | None) -> str:
    labels = {
        "en": "English",
        "fa": "Farsi / Persian",
        "mixed": "English + Farsi",
        "unknown": "Unknown",
    }
    return labels.get(code or "unknown", "Unknown")
