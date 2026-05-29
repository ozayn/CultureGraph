"""Parse Google Lens-style match payloads into lens search candidates."""

from __future__ import annotations

from typing import Any

from app.services.web_visual_search.types import WEB_VISUAL_SEARCH_SOURCE, LensSearchCandidate


def confidence_label_for_rank(rank: int) -> str:
    if rank <= 2:
        return "high"
    if rank <= 6:
        return "possible"
    return "weak"


def candidate_key(item: dict[str, Any]) -> str:
    return "|".join(
        str(item.get(key) or "").strip()
        for key in ("link", "image", "thumbnail", "title", "source")
    )


def parse_match_item(item: dict[str, Any], *, rank: int) -> LensSearchCandidate | None:
    title = str(item.get("title") or item.get("source") or "Web result").strip()
    if not title:
        title = "Web result"

    source = str(item.get("source") or WEB_VISUAL_SEARCH_SOURCE).strip() or WEB_VISUAL_SEARCH_SOURCE
    source_url = item.get("link")
    thumbnail_url = item.get("thumbnail")
    image_url = item.get("image") or thumbnail_url
    snippet = title if title != source else None

    if not any([source_url, thumbnail_url, image_url]):
        return None

    return LensSearchCandidate(
        title=title,
        source=source,
        source_url=str(source_url).strip() if source_url else None,
        thumbnail_url=str(thumbnail_url).strip() if thumbnail_url else None,
        image_url=str(image_url).strip() if image_url else None,
        snippet=snippet,
        source_rank=rank,
        confidence_label=confidence_label_for_rank(rank),
    )


def parse_lens_candidates(payload: dict[str, Any], *, max_results: int) -> list[LensSearchCandidate]:
    matches: list[dict[str, Any]] = []
    for key in ("visual_matches", "exact_matches"):
        section = payload.get(key)
        if isinstance(section, list):
            matches.extend(item for item in section if isinstance(item, dict))

    candidates: list[LensSearchCandidate] = []
    seen: set[str] = set()
    rank = 0
    for item in matches:
        key = candidate_key(item)
        if not key or key in seen:
            continue
        seen.add(key)
        rank += 1
        candidate = parse_match_item(item, rank=rank)
        if candidate is None:
            continue
        candidates.append(candidate)
        if len(candidates) >= max_results:
            break
    return candidates
