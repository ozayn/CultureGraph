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
    performance_indicators: list[str] = Field(default_factory=list)
    costume_clues: list[str] = Field(default_factory=list)
    posture_gesture: list[str] = Field(default_factory=list)
    brushwork_technique: list[str] = Field(default_factory=list)
    framing_cropping: list[str] = Field(default_factory=list)
    movement_depiction: list[str] = Field(default_factory=list)
    theatrical_indicators: list[str] = Field(default_factory=list)
    thematic_cues: list[str] = Field(default_factory=list)
    visual_tags: list[str] = Field(default_factory=list)


_BOOST_TERMS: dict[str, float] = {
    "ballet": 0.10,
    "dancer": 0.10,
    "dancers": 0.10,
    "dance": 0.08,
    "degas": 0.12,
    "pastel": 0.08,
    "performance": 0.07,
    "rehearsal": 0.07,
    "tutu": 0.08,
    "theatrical": 0.05,
    "impressionist": 0.04,
    "cropped": 0.04,
    "gesture": 0.03,
}

_PENALTY_TERMS: dict[str, float] = {
    "bather": -0.12,
    "bathers": -0.12,
    "bathing": -0.10,
    "pastoral": -0.08,
    "mytholog": -0.07,
    "nude": -0.05,
    "outdoor": -0.04,
}

_DANCE_SIGNAL_TOKENS = frozenset(
    {
        "ballet",
        "dancer",
        "dancers",
        "dance",
        "tutu",
        "rehearsal",
        "performance",
        "theatrical",
        "degas",
    }
)


def _dedupe_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in values:
        cleaned = re.sub(r"\s+", " ", raw.strip())
        if not cleaned or len(cleaned) < 2:
            continue
        key = normalize(cleaned)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(cleaned)
    return ordered


def _tokenize(text: str) -> set[str]:
    return {token for token in normalize(text).split() if len(token) > 2}


def _has_dance_signals(tag_blob: str, visual: VisualAnalysis | None) -> bool:
    tokens = _tokenize(tag_blob)
    if tokens & _DANCE_SIGNAL_TOKENS:
        return True
    if not visual:
        return False
    for group in (
        visual.performance_indicators,
        visual.theatrical_indicators,
        visual.costume_clues,
        visual.visual_tags,
    ):
        group_blob = normalize(" ".join(group))
        if _tokenize(group_blob) & _DANCE_SIGNAL_TOKENS:
            return True
    return False


def derive_visual_tags(visual: VisualAnalysis | None) -> list[str]:
    """Build high-signal tags from structured visual fields."""
    if not visual:
        return []

    candidates: list[str] = []
    candidates.extend(visual.visual_tags)
    candidates.extend(visual.performance_indicators)
    candidates.extend(visual.costume_clues)
    candidates.extend(visual.posture_gesture)
    candidates.extend(visual.brushwork_technique)
    candidates.extend(visual.framing_cropping)
    candidates.extend(visual.movement_depiction)
    candidates.extend(visual.theatrical_indicators)
    candidates.extend(visual.thematic_cues)
    candidates.extend(visual.style_signals)
    candidates.extend(visual.medium_clues)
    candidates.extend(visual.composition)
    candidates.extend(visual.clothing)

    tag_blob = normalize(" ".join(candidates))
    tokens = _tokenize(tag_blob)

    if tokens & {"ballet", "dancer", "dancers", "dance", "tutu"}:
        candidates.extend(["ballet", "dancers", "performance"])
    if "pastel" in tokens:
        candidates.append("pastel")
    if tokens & {"degas", "impressionist"} or "degas" in tag_blob:
        candidates.append("Degas-like")
    if tokens & {"cropped", "crop", "truncated"} or "cropped" in tag_blob:
        candidates.append("cropped figures")
    if tokens & {"theatrical", "stage", "rehearsal", "performance"}:
        candidates.append("theatrical pose")
    if tokens & {"rehearsal", "practice"}:
        candidates.append("rehearsal")
    if "impressionist" in tokens and tokens & {"ballet", "dance", "dancer", "dancers"}:
        candidates.append("Impressionist dance scene")

    return _dedupe_preserve_order(candidates)


def collect_weighted_visual_tags(visual: VisualAnalysis | None) -> list[str]:
    if not visual:
        return []
    return derive_visual_tags(visual)


def enrich_visual_analysis_fields(visual: VisualAnalysis | None) -> VisualAnalysis | None:
    if not visual:
        return None
    merged_tags = _dedupe_preserve_order([*visual.visual_tags, *derive_visual_tags(visual)])
    return visual.model_copy(update={"visual_tags": merged_tags[:24]})


def collect_visual_keywords(
    visual: VisualAnalysis | None,
    *,
    period_or_movement: str | None = None,
    ocr_label_text: str | None = None,
) -> list[str]:
    """Build deduplicated search tokens — high-signal tags first, generic subject last."""
    keywords: list[str] = []

    def extend(values: Iterable[str]) -> None:
        keywords.extend(_dedupe_preserve_order(values))

    if ocr_label_text:
        extend([ocr_label_text])

    if visual:
        extend(visual.visual_tags)
        extend(visual.performance_indicators)
        extend(visual.costume_clues)
        extend(visual.posture_gesture)
        extend(visual.brushwork_technique)
        extend(visual.framing_cropping)
        extend(visual.movement_depiction)
        extend(visual.theatrical_indicators)
        extend(visual.thematic_cues)
        extend(visual.composition)
        extend(visual.medium_clues)
        extend(visual.style_signals)
        extend(visual.clothing)
        extend(visual.notable_objects)
        extend(visual.period_clues)
        if visual.movement_style:
            extend([visual.movement_style])
        if visual.subject:
            extend([visual.subject])

    if period_or_movement:
        extend([period_or_movement])

    return _dedupe_preserve_order(keywords)


def visual_keywords_query(keywords: Iterable[str], *, limit: int = 8) -> str:
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


def visual_tag_ranking_adjustment(
    candidate_text: str,
    visual_tags: list[str],
    visual: VisualAnalysis | None = None,
) -> float:
    """Small ranking-only boost/penalty from distinctive visual tags — not identity confidence."""
    if not visual_tags:
        return 0.0

    haystack = normalize(candidate_text)
    tag_blob = normalize(" ".join(visual_tags))
    dance_context = _has_dance_signals(tag_blob, visual)

    adjustment = 0.0
    for term, weight in _BOOST_TERMS.items():
        if term in haystack and (term in tag_blob or (dance_context and term in _DANCE_SIGNAL_TOKENS)):
            adjustment += weight

    for term, weight in _PENALTY_TERMS.items():
        if term not in haystack:
            continue
        if dance_context or term in {"bather", "bathers", "bathing", "mytholog"}:
            adjustment += weight

    return max(-0.25, min(0.25, adjustment))


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

    if visual and visual.visual_tags:
        parts.append(f"Distinctive cues: {', '.join(visual.visual_tags[:5])}")
    elif visual and visual.subject:
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
