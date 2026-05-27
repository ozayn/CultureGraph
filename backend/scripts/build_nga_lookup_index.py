#!/usr/bin/env python3
"""Build a compact NGA open-data lookup index for CultureGraph."""

from __future__ import annotations

import csv
import io
import json
import urllib.request
from collections import defaultdict
from pathlib import Path

IMAGES_URL = (
    "https://raw.githubusercontent.com/NationalGalleryOfArt/opendata/main/data/published_images.csv"
)
OBJECTS_URL = (
    "https://raw.githubusercontent.com/NationalGalleryOfArt/opendata/main/data/objects.csv"
)
CONSTITUENTS_URL = (
    "https://raw.githubusercontent.com/NationalGalleryOfArt/opendata/main/data/objects_constituents.csv"
)
PEOPLE_URL = (
    "https://raw.githubusercontent.com/NationalGalleryOfArt/opendata/main/data/constituents.csv"
)
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "app" / "data" / "nga_lookup_index.json"
MAX_ENTRIES = 6000


def main() -> None:
    obj_image: dict[str, dict[str, str]] = {}
    with urllib.request.urlopen(IMAGES_URL, timeout=180) as response:
        reader = csv.DictReader(io.TextIOWrapper(response, encoding="utf-8"))
        for index, row in enumerate(reader):
            if row.get("openaccess") != "1" or row.get("viewtype") != "primary":
                continue
            object_id = row.get("depictstmsobjectid")
            if not object_id or object_id in obj_image:
                continue
            iiif_url = (row.get("iiifurl") or "").strip()
            iiif_thumb = (row.get("iiifthumburl") or "").strip()
            obj_image[object_id] = {
                "image_url": iiif_url or iiif_thumb,
                "image_thumbnail_url": iiif_thumb or iiif_url,
                "rights_label": "CC0 — National Gallery of Art Open Access",
            }
            if len(obj_image) >= MAX_ENTRIES:
                break
            if index and index % 20000 == 0:
                print(f"images scanned: {index}, mapped: {len(obj_image)}")

    obj_artist: dict[str, list[int]] = defaultdict(list)
    with urllib.request.urlopen(CONSTITUENTS_URL, timeout=180) as response:
        reader = csv.DictReader(io.TextIOWrapper(response, encoding="utf-8"))
        for index, row in enumerate(reader):
            if row.get("roletype") != "artist":
                continue
            obj_artist[row["objectid"]].append(int(row["constituentid"]))
            if index > 150000:
                break

    people: dict[str, str] = {}
    with urllib.request.urlopen(PEOPLE_URL, timeout=120) as response:
        reader = csv.DictReader(io.TextIOWrapper(response, encoding="utf-8"))
        for row in reader:
            people[row["constituentid"]] = (
                row.get("preferreddisplayname") or row.get("forwarddisplayname") or ""
            )

    entries: list[dict] = []
    with urllib.request.urlopen(OBJECTS_URL, timeout=240) as response:
        reader = csv.DictReader(io.TextIOWrapper(response, encoding="utf-8"))
        for index, row in enumerate(reader):
            object_id = row["objectid"]
            if object_id not in obj_image or row.get("accessioned") != "1":
                continue
            title = (row.get("title") or "").strip()
            if not title:
                continue

            artist = None
            for constituent_id in obj_artist.get(object_id, [])[:2]:
                artist = people.get(str(constituent_id))
                if artist:
                    break
            if not artist:
                artist = (row.get("attribution") or "").strip() or None

            entries.append(
                {
                    "object_id": object_id,
                    "title": title,
                    "artist": artist,
                    "date": (row.get("displaydate") or "").strip() or None,
                    "medium": (row.get("medium") or "").strip() or None,
                    "accession_number": (row.get("accessionnum") or "").strip() or None,
                    "begin_year": row.get("beginyear") or None,
                    "end_year": row.get("endyear") or None,
                    "image_url": obj_image[object_id]["image_url"],
                    "image_thumbnail_url": obj_image[object_id]["image_thumbnail_url"],
                    "object_url": (
                        f"https://www.nga.gov/collection/art-object-page.html?objectid={object_id}"
                    ),
                    "rights_label": obj_image[object_id]["rights_label"],
                }
            )
            if len(entries) >= MAX_ENTRIES:
                break
            if index and index % 25000 == 0:
                print(f"objects scanned: {index}, entries: {len(entries)}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(entries)} entries to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
