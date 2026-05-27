"""Structured visual extraction from artwork images (separate from catalog identification)."""

from __future__ import annotations

import re
from typing import Iterable

from pydantic import BaseModel, Field

from app.sources.matching import normalize


class VisualAnalysis(BaseModel):
    subject: str | None = None
    composition: list[str] = Field(default_factory=list)
    medium_clues: list[str] = Field(default_factory=list)
    period_clues: list[str] = Field(default_factory=list)
    clothing: list[str] = Field(default_factory=list)
    color_palette: list[str] = Field(default_factory=list)
    notable_objects: list[str] = Field(default_factory=list)
    style_signals: list[str] = Field(default_factory=list)
    movement_style: str | None = None


def collect_visual_keywords(
    visual: VisualAnalysis | None,
    *,
    period_or_movement: str | None = None,
    ocr_label_text: str | None = None,
) -> list[str]:
    """Build deduplicated search tokens for museum retrieval."""
    seen: set[str] = set()
    keywords: list[str] = []

    def add(value: str | None) -> None:
        if not value:
            return
        cleaned = re.sub(r"\s+", " ", value.strip())
        if not cleaned or len(cleaned) < 2:
            return
        key = normalize(cleaned)
        if key in seen:
            return
        seen.add(key)
        keywords.append(cleaned)

    if ocr_label_text:
        add(ocr_label_text)

    if visual:
        add(visual.subject)
        add(visual.movement_style)
        for group in (
            visual.composition,
            visual.medium_clues,
            visual.period_clues,
            visual.clothing,
            visual.notable_objects,
            visual.style_signals,
        ):
            for item in group:
                add(item)

    if period_or_movement:
        add(period_or_movement)

    return keywords


def visual_keywords_query(keywords: Iterable[str], *, limit: int = 6) -> str:
    """Compact query string for open collection search."""
    parts: list[str] = []
    for keyword in keywords:
        text = keyword.strip()
        if not text:
            continue
        parts.append(text)
        if len(parts) >= limit:
            break
    return " · ".join(parts)


def build_visual_summary(
    visual: VisualAnalysis | None,
    *,
    period_or_movement: str | None,
    vision_confidence: float,
) -> str:
    """Non-authoritative description for UI — no invented catalog titles."""
    parts: list[str] = []

    if visual and visual.movement_style:
        parts.append(visual.movement_style)
    elif period_or_movement:
        parts.append(period_or_movement)

    if visual and visual.subject:
        parts.append(f"Subject appears to be {visual.subject.rstrip('.')}")

    if visual and visual.medium_clues:
        medium = ", ".join(visual.medium_clues[:2])
        parts.append(f"Medium clues: {medium}")

    if not parts:
        parts.append("Visual analysis complete — verify identification against museum collections")

    summary = ". ".join(parts)
    if not summary.endswith("."):
        summary += "."
    summary += " Collection search will refine possible matches."
    if vision_confidence < 0.55:
        summary += " Image-only analysis is uncertain."
    return summary


_OCR_TITLE_PATTERNS = (
    re.compile(r"^title\s*:\s*(.+)$", re.I | re.M),
    re.compile(r"^work\s*:\s*(.+)$", re.I | re.M),
)


def extract_title_from_ocr(ocr_text: str | None) -> str | None:
    if not ocr_text or not ocr_text.strip():
        return None
    for pattern in _OCR_TITLE_PATTERNS:
        match = pattern.search(ocr_text.strip())
        if match:
            title = match.group(1).strip().strip('"')
            return title or None
    lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]
    if len(lines) == 1 and len(lines[0]) >= 8:
        return lines[0]
    return None


def extract_artist_from_ocr(ocr_text: str | None) -> str | None:
    if not ocr_text or not ocr_text.strip():
        return None
    match = re.search(
        r"(?:artist|attributed to|by)\s*:\s*(.+)$",
        ocr_text.strip(),
        re.I | re.M,
    )
    if match:
        artist = match.group(1).strip().strip('"')
        return artist or None
    return None
