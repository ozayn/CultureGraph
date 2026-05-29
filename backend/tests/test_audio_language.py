"""Language detection for bilingual audio notes."""

from __future__ import annotations

import pytest

from app.services.audio_language import (
    detect_transcript_language,
    map_whisper_language,
    refine_detected_language,
)


def test_detect_english_transcript() -> None:
    assert detect_transcript_language("I notice the red clothing.") == "en"


def test_detect_farsi_transcript() -> None:
    assert detect_transcript_language("لباس قرمز و چهره رسمی کودک را می‌بینم.") == "fa"


def test_detect_mixed_transcript() -> None:
    assert detect_transcript_language("I notice the red لباس and formal pose.") == "mixed"


def test_map_whisper_persian_codes() -> None:
    assert map_whisper_language("persian") == "fa"
    assert map_whisper_language("english") == "en"


def test_refine_conflicting_whisper_and_script_to_mixed() -> None:
    assert refine_detected_language("I notice the red clothing.", "persian") == "mixed"
