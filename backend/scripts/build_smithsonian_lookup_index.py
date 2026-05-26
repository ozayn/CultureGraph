#!/usr/bin/env python3
"""Build a compact Smithsonian Open Access lookup index for CultureGraph."""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

S3_BASE = "https://smithsonian-open-access.s3-us-west-2.amazonaws.com/metadata/edan"
OUTPUT_PATH = (
    Path(__file__).resolve().parent.parent / "app" / "data" / "smithsonian_lookup_index.json"
)

# Art-focused Smithsonian units used for official image lookup.
UNITS: dict[str, str] = {
    "saam": "Smithsonian American Art Museum",
    "npg": "National Portrait Gallery",
    "hmsg": "Hirshhorn Museum and Sculpture Garden",
    "fsg": "National Museum of Asian Art",
    "nmafa": "National Museum of African Art",
}

MAX_ENTRIES_PER_UNIT = 1200
RIGHTS_LABEL = "CC0 — Smithsonian Open Access"


def main() -> None:
    entries: list[dict] = []
    for unit_code, source_name in UNITS.items():
        unit_entries = _collect_unit_entries(unit_code, source_name)
        entries.extend(unit_entries)
        print(f"{unit_code}: {len(unit_entries)} entries")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(entries)} entries to {OUTPUT_PATH}")


def _collect_unit_entries(unit_code: str, source_name: str) -> list[dict]:
    index_url = f"{S3_BASE}/{unit_code}/index.txt"
    with urllib.request.urlopen(index_url, timeout=120) as response:
        file_urls = [
            line.strip()
            for line in response.read().decode("utf-8").splitlines()
            if line.strip().endswith(".txt")
        ]

    results: list[dict] = []
    seen_ids: set[str] = set()

    for file_url in file_urls:
        if len(results) >= MAX_ENTRIES_PER_UNIT:
            break
        with urllib.request.urlopen(file_url, timeout=180) as response:
            for raw_line in response:
                if len(results) >= MAX_ENTRIES_PER_UNIT:
                    break
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                entry = _record_to_entry(record, source_name)
                if not entry:
                    continue
                object_id = entry["object_id"]
                if object_id in seen_ids:
                    continue
                seen_ids.add(object_id)
                results.append(entry)

    return results


def _record_to_entry(record: dict, default_source_name: str) -> dict | None:
    content = record.get("content") or {}
    descriptive = content.get("descriptiveNonRepeating") or {}
    freetext = content.get("freetext") or {}

    usage = (descriptive.get("metadata_usage") or {}).get("access")
    if usage and str(usage).upper() != "CC0":
        return None

    rights_entries = freetext.get("objectRights") or []
    if rights_entries:
        rights_text = " ".join(item.get("content", "") for item in rights_entries).upper()
        if rights_text and "CC0" not in rights_text:
            return None

    online_media = descriptive.get("online_media") or {}
    media_items = online_media.get("media") or []
    image_media = next(
        (item for item in media_items if (item.get("type") or "").lower() == "images"),
        media_items[0] if media_items else None,
    )
    if not image_media:
        return None

    image_url, thumbnail_url = _pick_image_urls(image_media)
    if not image_url:
        return None

    title = (
        (descriptive.get("title") or {}).get("content")
        or record.get("title")
        or ""
    ).strip()
    if not title:
        return None

    artist = _freetext_value(freetext, "Artist") or _freetext_value(freetext, "Maker")
    date = _freetext_value(freetext, "Date")
    medium = _freetext_value(freetext, "Medium")
    accession = _freetext_value(freetext, "Object number") or _freetext_value(
        freetext, "Accession Number"
    )
    museum_name = descriptive.get("data_source") or default_source_name
    object_id = descriptive.get("record_ID") or record.get("url") or record.get("id")
    object_url = descriptive.get("record_link")
    begin_year, end_year = _parse_year_range(date, content.get("indexedStructured") or {})

    return {
        "object_id": object_id,
        "title": title,
        "artist": artist,
        "date": date,
        "medium": medium,
        "accession_number": accession,
        "begin_year": begin_year,
        "end_year": end_year,
        "image_url": image_url,
        "image_thumbnail_url": thumbnail_url,
        "object_url": object_url,
        "source_name": museum_name,
        "rights_label": RIGHTS_LABEL,
    }


def _pick_image_urls(media_item: dict) -> tuple[str | None, str | None]:
    resources = media_item.get("resources") or []
    screen_url = None
    thumb_url = None
    jpeg_url = None

    for resource in resources:
        label = (resource.get("label") or "").lower()
        url = resource.get("url")
        if not url:
            continue
        if "thumbnail" in label:
            thumb_url = url
        elif "screen" in label:
            screen_url = url
        elif "jpeg" in label and not jpeg_url:
            jpeg_url = url

    image_url = screen_url or jpeg_url or media_item.get("content") or media_item.get("thumbnail")
    thumbnail_url = thumb_url or media_item.get("thumbnail") or image_url
    return image_url, thumbnail_url


def _freetext_value(freetext: dict, label: str) -> str | None:
    for item in freetext.get("name", []) + freetext.get("date", []) + freetext.get(
        "physicalDescription", []
    ) + freetext.get("identifier", []):
        if item.get("label") == label:
            content = (item.get("content") or "").strip()
            if content:
                return content
    return None


def _parse_year_range(
    date_text: str | None,
    indexed: dict,
) -> tuple[str | None, str | None]:
    years: list[int] = []
    if date_text:
        years.extend(int(match) for match in re.findall(r"\d{4}", date_text))
        decades = [int(match) for match in re.findall(r"(\d{3})0s", date_text)]
        for decade in decades:
            years.extend([decade, decade + 9])

    for decade in indexed.get("date") or []:
        match = re.match(r"(\d{3})0s", str(decade))
        if match:
            base = int(match.group(1)) * 10
            years.extend([base, base + 9])

    if not years:
        return None, None

    begin = min(years)
    end = max(years)
    return str(begin), str(end)


if __name__ == "__main__":
    main()
