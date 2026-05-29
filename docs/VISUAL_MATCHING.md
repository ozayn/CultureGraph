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

```bash
export NGA_INDEX_LIMIT=500   # start small locally
python scripts/build_nga_image_index.py
```

The script:

- loads NGA open-data records with image URLs
- upserts `collection_artworks`
- downloads thumbnails
- computes/caches embeddings
- stores vectors in `collection_image_embeddings`

Re-running the script skips records that already have embeddings for the active model.

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `VISUAL_EMBEDDING_BACKEND` | `openclip` | `openclip` or `test` |
| `VISUAL_EMBEDDING_MODEL` | `ViT-B-32` | OpenCLIP model name |
| `VISUAL_EMBEDDING_PRETRAINED` | `openai` | OpenCLIP weights tag |
| `NGA_INDEX_LIMIT` | `2000` | Max records indexed by build script |
| `VISUAL_MATCH_TOP_K` | `12` | Candidates returned to UI |

## Production / Railway notes

- Do **not** run full indexing on every deploy.
- Run `build_nga_image_index.py` manually or as a one-off background job.
- Expect several hundred MB of Python deps if OpenCLIP/torch are installed in the API container.
- Expect additional Postgres storage for embeddings (~512 floats per indexed artwork).
- For Railway MVP, consider:
  - indexing only NGA
  - keeping `NGA_INDEX_LIMIT` low initially
  - running indexing from a separate worker/container

## Current scope

- Museum-scoped visual search for **National Gallery of Art** visits only.
- Uses the cropped display image when available.
- Honest confidence labels: `high`, `possible`, `weak`.
- UI copy: **Best visual matches**, not verified identification.

## Future plan

- Smithsonian, Met, and Art Institute visual indexes
- pgvector-backed nearest-neighbor search
- Background indexing jobs with progress reporting
- Label OCR as additional evidence after visual shortlist
- Optional AI explanation only after the user selects a candidate
