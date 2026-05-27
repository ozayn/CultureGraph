"""Medium / object-type classification for museum image lookup ranking."""

from __future__ import annotations

import re
from typing import Literal

MediumType = Literal["2d", "3d", "unknown"]
MediumTypeFilter = Literal["2d", "3d", "any"]

MEDIUM_2D_KEYWORDS = (
    "painting",
    "paint",
    "painted",
    "oil",
    "acrylic",
    "tempera",
    "pastel",
    "drawing",
    "drawn",
    "charcoal",
    "graphite",
    "chalk",
    "crayon",
    "watercolor",
    "watercolour",
    "gouache",
    "ink",
    "pen",
    "pencil",
    "print",
    "printing",
    "lithograph",
    "etching",
    "engraving",
    "aquatint",
    "drypoint",
    "mezzotint",
    "woodcut",
    "monotype",
    "canvas",
    "paper",
    "panel",
    "board",
    "card",
    "photograph",
    "photo",
    "collage",
)

MEDIUM_3D_KEYWORDS = (
    "sculpture",
    "sculptural",
    "statue",
    "figurine",
    "bust",
    "relief",
    "cast",
    "bronze",
    "brass",
    "marble",
    "stone",
    "plaster",
    "plastiline",
    "terracotta",
    "ceramic",
    "clay",
    "wax",
    "beeswax",
    "armature",
    "fabric",
    "wire",
    "metal",
    "wooden base",
    "plinth",
    "object",
    "installation",
    "assemblage",
)

# Painted sculpture cues — still 3D despite "painted"
MEDIUM_3D_STRONG = (
    "plaster",
    "plastiline",
    "armature",
    "bronze",
    "marble",
    "cast",
    "statue",
    "sculpture",
    "figurine",
    "beeswax",
)


def normalize_medium_text(value: str | None) -> str:
    if not value:
        return ""
    lowered = value.lower()
    cleaned = re.sub(r"[^a-z0-9\s]", " ", lowered)
    return re.sub(r"\s+", " ", cleaned).strip()


def classify_medium(value: str | None) -> MediumType:
    text = normalize_medium_text(value)
    if not text:
        return "unknown"

    score_2d = sum(1 for keyword in MEDIUM_2D_KEYWORDS if keyword in text)
    score_3d = sum(1 for keyword in MEDIUM_3D_KEYWORDS if keyword in text)
    for keyword in MEDIUM_3D_STRONG:
        if keyword in text:
            score_3d += 2

    if score_3d > score_2d and score_3d > 0:
        return "3d"
    if score_2d > 0:
        return "2d"
    if score_3d > 0:
        return "3d"
    return "unknown"


def medium_type_label(medium_type: MediumType) -> str:
    return {"2d": "2D work", "3d": "3D work", "unknown": "Unknown type"}[medium_type]


def infer_expected_medium_type(
    *,
    artwork_medium: str | None,
    ai_medium: str | None,
    notes: str | None = None,
    medium_override: str | None = None,
) -> MediumType:
    if medium_override and medium_override.strip():
        classified = classify_medium(medium_override)
        if classified != "unknown":
            return classified

    for value in (artwork_medium, ai_medium, notes):
        classified = classify_medium(value)
        if classified != "unknown":
            return classified
    return "unknown"


def resolve_medium_type_filter(
    expected: MediumType,
    medium_type_param: str | None,
) -> MediumTypeFilter:
    del expected
    normalized = (medium_type_param or "").strip().lower()
    if normalized in {"2d", "3d", "any"}:
        return normalized  # type: ignore[return-value]
    return "any"


def medium_score_adjustment(query_type: MediumType, candidate_type: MediumType) -> float:
    if query_type == "unknown" or candidate_type == "unknown":
        return 0.0
    if query_type == candidate_type:
        return 0.14
    return -0.22


def mediums_match(query_type: MediumType, candidate_type: MediumType) -> bool | None:
    if query_type == "unknown" or candidate_type == "unknown":
        return None
    return query_type == candidate_type


def build_match_reasons(
    *,
    title_score: float,
    artist_score: float,
    medium_match: bool | None,
    has_title_query: bool,
    artist_text: str,
) -> list[str]:
    reasons: list[str] = []
    if has_title_query and title_score >= 0.65:
        reasons.append("Title match")
    elif has_title_query and title_score >= 0.35:
        reasons.append("Partial title match")

    if artist_text and artist_score >= 0.72:
        reasons.append("Artist match")
    elif artist_text and artist_score >= 0.48:
        reasons.append("Related artist")

    if medium_match is True:
        reasons.append("Medium match")
    elif medium_match is False:
        reasons.append("Medium mismatch")

    return reasons[:4]
