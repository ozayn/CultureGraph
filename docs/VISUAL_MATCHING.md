# Visual artwork matching

CultureGraph Phase 1 matches uploaded artwork crops against museum collection thumbnails using image embeddings — similar to a museum-specific Google Lens.

## Pipeline

1. User crops their artwork photo.
2. `POST /api/artworks/{id}/visual-match` embeds the crop with OpenCLIP.
3. The service searches precomputed NGA collection embeddings in Postgres.
4. Results are lightly reranked with saved artist/title/medium hints.
5. The user confirms a candidate before applying catalog image/metadata.
6. Optional Claude enrichment remains available for style analysis and annotations after matching.

Semantic / text-based collection search is now a fallback (`Try text-based search`), not the primary path.

## Local setup

### 1. Install visual dependencies

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-visual.txt
```

For unit tests only (no real CLIP model):

```bash
export VISUAL_EMBEDDING_BACKEND=test
```

On Apple Silicon (MacBook Pro M4), OpenCLIP uses PyTorch MPS automatically when available.

### 2. Run migrations

```bash
alembic upgrade head
```

This creates:

- `collection_artworks`
- `collection_image_embeddings`

Embeddings are stored as JSON float arrays for MVP. pgvector can replace this later.

### 3. Build the text lookup index (if needed)

```bash
python scripts/build_nga_lookup_index.py
```

### 4. Build the visual index

Recommended first test on a MacBook Pro M4:

```bash
python scripts/build_nga_image_index.py --limit 500
```

CLI options:

| Flag | Purpose |
|------|---------|
| `--limit N` | Process at most N records in this run |
| `--resume` | Continue from `data/nga_visual_index_state.json` offset |
| `--rebuild` | Re-embed even when embeddings already exist |
| `--batch-size N` | Commit and log progress every N records (default 25) |
| `--dry-run` | Log planned work without DB writes or embeddings |

Progress logging example:

```text
Indexed 120 / 500 artworks
```

The script:

- loads NGA open-data records with image URLs
- upserts `collection_artworks`
- downloads thumbnails into `data/nga_thumbnail_cache/` (reused on later runs)
- computes embeddings with OpenCLIP (`embedding_model` stored per row)
- stores vectors in `collection_image_embeddings`
- skips records already embedded unless `--rebuild`
- prints timing metrics at the end (`elapsed_s=...`)

Resume a larger build:

```bash
python scripts/build_nga_image_index.py --limit 500 --resume
python scripts/build_nga_image_index.py --limit 1500 --resume
```

## Estimated disk usage (local M4)

| Item | Approximate size |
|------|------------------|
| OpenCLIP + PyTorch wheels | 400–800 MB in `.venv` |
| Thumbnail cache (`--limit 500`) | 25–75 MB |
| Thumbnail cache (`--limit 2000`) | 100–300 MB |
| Postgres embeddings (`--limit 2000`) | ~5–15 MB JSON vectors |

Thumbnail cache and resume state live under `backend/data/` and are gitignored.

## Estimated runtime (MacBook Pro M4)

Rough order of magnitude with `VISUAL_EMBEDDING_BACKEND=openclip` and MPS:

| Batch | New embeddings | Typical wall time |
|-------|----------------|-------------------|
| `--limit 500` | ~400–500 | 15–35 minutes |
| `--limit 2000` | ~1500–2000 | 1–2.5 hours |

Re-runs with cached thumbnails and existing embeddings are much faster because the script skips completed records unless `--rebuild`.

Dry-run a batch without writing:

```bash
python scripts/build_nga_image_index.py --limit 50 --dry-run
```

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `VISUAL_EMBEDDING_BACKEND` | `openclip` | `openclip` or `test` |
| `VISUAL_EMBEDDING_MODEL` | `ViT-B-32` | OpenCLIP model name |
| `VISUAL_EMBEDDING_PRETRAINED` | `openai` | OpenCLIP weights tag |
| `NGA_INDEX_LIMIT` | `2000` | Default `--limit` when flag omitted |
| `VISUAL_MATCH_TOP_K` | `12` | Candidates returned to UI |

## Admin status

`GET /api/admin/visual-index-status` returns:

- `indexed_count`
- `embedding_model`
- `last_updated`
- `thumbnail_cache_size` (bytes)

The admin dashboard shows this card beside upload storage health.

## Production / Railway notes

- Do **not** run full indexing on every deploy.
- Run `build_nga_image_index.py` manually or as a one-off background job.
- Expect several hundred MB of Python deps if OpenCLIP/torch are installed in the API container.
- Expect additional Postgres storage for embeddings (~512 floats per indexed artwork).
- For Railway MVP, consider:
  - indexing only NGA
  - keeping `--limit` low initially
  - running indexing from a separate worker/container

## Current scope

- Museum-scoped visual search for **National Gallery of Art** visits only.
- Uses the cropped display image when available.
- Honest confidence labels: `high`, `possible`, `weak`.
- UI copy: **Best visual matches**, not verified identification.
- Empty index UI: **NGA visual index is still building**; once indexed, the UI shows artwork counts.

## Future plan

- Smithsonian, Met, and Art Institute visual indexes
- pgvector-backed nearest-neighbor search
- Background indexing jobs with progress reporting
- Label OCR as additional evidence after visual shortlist
- Optional AI explanation only after the user selects a candidate
