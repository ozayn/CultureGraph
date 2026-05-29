# AI and artwork recognition

CultureGraph recognizes artworks through **multiple complementary signals**. No single model is authoritative. Admins review candidates before anything is saved to the catalog.

## Philosophy: human-in-the-loop

```
         ┌──────────────┐
         │ User photo   │
         └──────┬───────┘
                ▼
    ┌───────────────────────┐
    │  Recognition signals │  ← Claude, OpenCLIP, text lookup, OCR, SerpApi
    └───────────┬───────────┘
                ▼
    ┌───────────────────────┐
    │  Candidates + hints  │  ← never auto-written to artwork row
    └───────────┬───────────┘
                ▼
    ┌───────────────────────┐
    │  Admin review + apply │  ← PUT /api/artworks/{id}
    └───────────────────────┘
```

- **Ephemeral:** visual-match, lens-search, manual lookup GET responses
- **Persisted only after apply:** `catalog_*` fields, title/artist/medium, or replacing `image_url`
- **Enrichment cache:** `artworks.enrichment_lookup` + `research_notes` — AI drafts, not final catalog truth

## Pipeline overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│ CAPTURE                                                                  │
│  Upload photo → set artwork crop region → optional wall label photo      │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ AUTO ENRICHMENT (background)                                             │
│  1. Claude vision     → ResearchDraft + VisualAnalysis                   │
│  2. Text lookup       → museum catalog candidates (semantic/fuzzy)       │
│  3. Identification  → catalog_match | possible_match | style_subject     │
│  4. Save            → research_notes + enrichment_lookup JSON            │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌───────────────┐         ┌─────────────────┐         ┌─────────────────┐
│ Visual match  │         │ Web lens search │         │ Text lookup     │
│ (manual btn)  │         │ (manual btn)    │         │ (manual / sheet)│
│ OpenCLIP+NGA  │         │ SerpApi         │         │ GET lookup-image│
└───────────────┘         └─────────────────┘         └─────────────────┘
```

Auto-enrichment does **not** call visual-match or lens-search. Those are separate admin actions in the AI assistant panel.

## Recognition sources

### 1. Claude vision and research

| | |
|--|--|
| **What** | Multimodal analysis: summary, style/subject tags, `possible_title/artist`, visual hypotheses, suggested annotation pins |
| **When** | Enrichment pipeline; standalone `POST /api/artworks/{id}/research` |
| **Module** | `app/services/claude_research.py`, `artwork_enrichment.py` |
| **Stored** | `research_notes` table; enrichment snapshot in `artworks.enrichment_lookup` |
| **UI** | Identification panel, style analysis, metadata apply, annotation suggestions |

Without `ANTHROPIC_API_KEY`, a deterministic mock provider runs for development.

### 2. Museum-scoped text lookup

| | |
|--|--|
| **What** | Searches offline museum JSON indexes by title/artist with semantic expansion and fuzzy fallback |
| **When** | Enrichment stage `searching_collections`; manual lookup sheet; `GET /lookup-image` |
| **Routing** | Visit museum → NGA, Smithsonian, Met, or Art Institute; `broaden_sources` adds Wikimedia |
| **Module** | `artwork_lookup.py`, `lookup_stages.py`, `semantic_retrieval.py`, `app/sources/*.py` |
| **Stored** | Cached in `enrichment_lookup.lookup` after enrichment; otherwise ephemeral |
| **UI** | `LookupCandidateList`, `ArtworkImageLookupPanel` |

Query priority: label OCR → manual overrides → AI title → saved title → artist notes → visual keywords.

See [integrations/museum-lookup.md](integrations/museum-lookup.md).

### 3. NGA visual index (OpenCLIP)

| | |
|--|--|
| **What** | Image embedding similarity against pre-indexed NGA collection thumbnails |
| **Why OpenCLIP** | Museum text lookup fails on image-only visits (no title on wall label). Embeddings enable “find this painting” from a crop without OCR. Offline index keeps query latency low and scopes results to NGA open data. |
| **When** | Manual **Find artwork match**; requires built index |
| **Model** | `ViT-B-32` + `openai` weights (configurable); Apple Silicon uses MPS |
| **Module** | `visual_embedding.py`, `visual_matching.py`, `nga_visual_index.py` |
| **Stored** | Index in `collection_artworks` + `collection_image_embeddings`; match results ephemeral |
| **UI** | `VisualMatchCandidateList` |

Build offline: [integrations/visual-matching.md](integrations/visual-matching.md).

### 4. Semantic retrieval

Not a separate API — it powers text lookup quality:

- Title normalization (strip “Study for…”, articles)
- Subject expansions (“four dancers” → ballet phrases)
- Multi-phrase scoring and tier labels (`high` / `possible` / `weak`)

Module: `semantic_retrieval.py`, `lookup_ranking.py`.

### 5. Label OCR

| | |
|--|--|
| **What** | Transcribes museum wall label text |
| **When** | On `POST /label-image`; also read by Claude during enrichment |
| **Provider** | `ClaudeLabelOcrProvider` (or placeholder if no API key) |
| **Module** | `label_ocr.py`, `visual_analysis.py` (title/artist extraction) |
| **Stored** | `artworks.label_ocr_text` — highest-priority lookup query source |
| **UI** | Indirect — feeds enrichment and lookup hints |

### 6. SerpApi web visual search (lens fallback)

| | |
|--|--|
| **What** | Third-party Google Lens results (similar images on the web) |
| **When** | Manual **Try web visual search** when museum index is empty or weak |
| **Requires** | `SERPAPI_API_KEY`, `PUBLIC_API_BASE_URL` for `/uploads/` images |
| **Module** | `lens_search.py` |
| **Stored** | Ephemeral |
| **UI** | `LensSearchCandidateList` (separate dashed section) |

Not an official Google API. See [integrations/lens-search.md](integrations/lens-search.md).

### 7. Image proxy

| | |
|--|--|
| **What** | Server-side fetch of museum HTTPS thumbnails (allowlisted hosts) |
| **When** | Frontend displays external catalog images |
| **Endpoint** | `GET /api/image-proxy?url=` |
| **Stored** | None |

## Identification modes

After enrichment, `build_identification` calibrates a verdict:

| Mode | Meaning |
|------|---------|
| `catalog_match` | Strong agreement between vision and top catalog candidate |
| `possible_match` | Plausible catalog hit, needs review |
| `style_subject` | No exact match — style/subject analysis only |
| `exact_not_found` | Exact-artwork search found no suitable hit |

## What is persisted vs ephemeral

| Output | Persisted? | Where |
|--------|------------|-------|
| User photo + crop | Yes | `artworks.image_*`, `crop_*_percent` |
| Label OCR text | Yes | `artworks.label_ocr_text` |
| Research draft | Yes | `research_notes`, `enrichment_lookup` |
| Visual match candidates | No | Until user applies via PUT |
| Lens search candidates | No | Until user applies |
| Manual lookup GET | No | Unless from enrichment cache |
| NGA embeddings | Yes | `collection_image_embeddings` |
| Applied catalog metadata | Yes | `catalog_*`, title, artist, etc. |

## Known limitations

- **Image-only recognition is still imperfect** — without label OCR or saved metadata, text lookup and identification often fall back to `style_subject`.
- **Visual index is NGA-first** — OpenCLIP matching only runs for National Gallery of Art visits today.
- **Uploads require persistent storage on Railway** — ephemeral disk loses photos on redeploy; see [storage/upload-storage.md](storage/upload-storage.md).
- **SerpApi requires public image URLs** — local `/uploads/` paths need `PUBLIC_API_BASE_URL` or a tunnel.
- **Disconnected tools** — visual match, lens search, and enrichment do not share a unified ranker yet.
- **Text lookup ≠ visual similarity** — a correct painting may be missed if the title guess is wrong.

## Future directions

See [roadmap/roadmap.md](roadmap/roadmap.md). Recognition-specific plans:

- Smithsonian / Met / AIC **visual indexes** (same OpenCLIP pipeline as NGA)
- **pgvector** for scalable nearest-neighbor search
- **Google Cloud Vision** label OCR (cheaper/deterministic complement to Claude)
- Stronger **image-only** path (fuse visual match into enrichment automatically)
- **Multilingual** label OCR and research (Farsi audio notes already supported)
- **Graph relationships** between entities, visits, and artworks

## Related docs

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [integrations/visual-matching.md](integrations/visual-matching.md)
- [integrations/lens-search.md](integrations/lens-search.md)
- [integrations/museum-lookup.md](integrations/museum-lookup.md)
- [ai/audio-notes.md](ai/audio-notes.md)
- [ENVIRONMENT.md](ENVIRONMENT.md)
