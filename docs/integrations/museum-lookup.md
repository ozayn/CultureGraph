# Museum collection lookup

CultureGraph searches **offline museum open-data indexes** for catalog records matching an artwork’s title, artist, and medium hints. This is the backbone of enrichment and the manual “Find official image” flow.

## How routing works

Visit museum name → lookup source:

| Museum context | Source |
|----------------|--------|
| National Gallery of Art | `nga` |
| Smithsonian museums | `smithsonian` |
| Metropolitan Museum of Art | `met` |
| Art Institute of Chicago | `aic` |
| Broaden search | `all` + Wikimedia fallback |

Module: `app/sources/routing.py` → `resolve_lookup_sources`.

## Query building

`build_artwork_lookup_query` chooses search terms in priority order:

1. **Label OCR** (`ocr_label`) — from `label_ocr_text`
2. **Manual overrides** — title/artist from lookup sheet
3. **AI title** — `possible_title` from latest research
4. **Saved title** — artwork row
5. **Artist notes** — personal notes on visit/artwork

Enrichment uses `build_retrieval_lookup_query` which also considers visual hypotheses and keywords from Claude.

## Lookup stages

`lookup_artwork_candidates_staged` collects and ranks candidates:

```
semantic → fuzzy → artist_fallback → broad
```

- **Semantic:** expanded phrases, title/artist similarity (`semantic_retrieval.py`)
- **Fuzzy:** tolerant string matching
- **Artist fallback:** search by artist when title fails
- **Broad:** relaxed thresholds; optional Wikimedia

Tiers: `high`, `possible`, `weak` — weak results may appear as “related candidates.”

## API

### Manual lookup

```
GET /api/artworks/{id}/lookup-image
```

Query params: `title_override`, `artist_override`, `source`, `search_mode=broad`, `medium_type`, `broaden_sources`.

### Enrichment (automatic)

Lookup runs in stage `searching_collections` and is cached in `artworks.enrichment_lookup.lookup`.

## Index data

| Source | Index file / origin |
|--------|---------------------|
| NGA | `app/data/nga_lookup_index.json` (build via `scripts/build_nga_lookup_index.py`) |
| Smithsonian | `app/data/smithsonian_lookup_index.json` |
| Met, AIC | Fetched/built per source modules |

Rebuild text indexes after museum open-data updates.

## UI

- **Enrichment panel** — `LookupCandidateList` when “Try text-based search” is active
- **Artwork image lookup sheet** — manual search with medium filter and apply review checkboxes

## Visual vs text lookup

| | Text lookup | Visual match (OpenCLIP) |
|--|-------------|-------------------------|
| Input | Title/artist/OCR/keywords | Cropped photo |
| Scope | Routed museum(s) | NGA only (today) |
| Index | JSON title search | Embedding vectors |
| Best for | Known or OCR’d titles | Image-only identification |

See [integrations/visual-matching.md](visual-matching.md) and [AI_RECOGNITION.md](../AI_RECOGNITION.md).

## Related docs

- [AI_RECOGNITION.md](../AI_RECOGNITION.md)
- [integrations/visual-matching.md](visual-matching.md)
