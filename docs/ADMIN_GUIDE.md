# Admin guide

CultureGraph is **public to browse** and **private to edit**. Only Google accounts in `ADMIN_EMAILS` can sign in and mutate data.

## Access

1. Configure `GOOGLE_CLIENT_ID`, `ADMIN_EMAILS`, and `JWT_SECRET` on the API.
2. Set matching `NEXT_PUBLIC_GOOGLE_CLIENT_ID` on the frontend.
3. Sign in via Google on any page with edit controls.
4. Open **Admin dashboard** at `/admin`.

## Admin dashboard (`/admin`)

Browse and maintain database records.

| Tab | Contents |
|-----|----------|
| Visits | Museum trips |
| Artworks | Photos, catalog fields |
| Annotations | Pin notes |
| Entities | Cultural entities (artists, movements, …) |
| Research notes | AI research drafts |

Features:

- Search and pagination
- Bulk select + delete
- Summary count cards

### Health cards

**Upload storage** — from `GET /api/admin/upload-health`:

| Field | Meaning |
|-------|---------|
| `upload_dir` | Resolved upload root |
| `persistent` | `true` when `UPLOAD_DIR=/app/uploads` on Railway |
| `missing_count` | DB paths with no file on disk |
| Clear missing | `POST /api/admin/upload-health/clear-missing` — strips broken paths |

**NGA visual index** — from `GET /api/admin/visual-index-status`:

| Field | Meaning |
|-------|---------|
| `indexed_count` | Embeddings in Postgres for active model |
| `embedding_model` | e.g. `ViT-B-32:openai` |
| `last_updated` | Latest embedding timestamp |
| `thumbnail_cache_size` | Local cache bytes (build machine) |

## Artwork recognition tools (admin)

On the artwork detail **AI assistant** panel (admin + photo + crop):

| Button | Endpoint | Purpose |
|--------|----------|---------|
| Find artwork match | `POST /api/artworks/{id}/visual-match` | OpenCLIP vs NGA index |
| Try web visual search | `POST /api/artworks/{id}/lens-search` | SerpApi fallback |
| Try text-based search | `POST /api/artworks/{id}/enrichment?exact_artwork=true` | Semantic catalog search |
| Run AI again | `POST /api/artworks/{id}/enrichment` | Full Claude + lookup pipeline |

**Find / Replace official image** sheet — `GET /api/artworks/{id}/lookup-image` with manual title/artist filters.

Nothing auto-applies. Use **Use image** / **Use image + metadata** on candidates, or the metadata review checkbox flow.

## Offline operations

### NGA text lookup index

```bash
cd backend
.venv/bin/python scripts/build_nga_lookup_index.py
```

Writes `app/data/nga_lookup_index.json`.

### NGA visual index

```bash
.venv/bin/python scripts/build_nga_image_index.py --limit 500
```

See [integrations/visual-matching.md](integrations/visual-matching.md).

### Seed development data

```bash
.venv/bin/python scripts/seed.py
```

Development only — not used by pytest.

### Clean accidental test data from dev DB

```bash
./scripts/cleanup-test-data.sh
```

## Admin API summary

All `/api/admin/*` routes require admin JWT **and** email in `ADMIN_EMAILS`.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/admin/summary` | Table counts |
| GET | `/api/admin/upload-health` | Upload persistence |
| POST | `/api/admin/upload-health/clear-missing` | Strip broken upload refs |
| GET | `/api/admin/visual-index-status` | NGA index stats |
| GET | `/api/admin/{visits,artworks,annotations,entities,research-notes}` | Paginated lists |
| POST | `/api/admin/{resource}/bulk-delete` | Bulk delete |

## Post-deploy checklist

1. Sign in with an `ADMIN_EMAILS` account.
2. `GET /api/admin/upload-health` → `persistent: true`, `missing_count: 0`.
3. Upload a test artwork photo → redeploy → image still loads.
4. `GET /api/admin/visual-index-status` → `indexed_count` > 0 (after index build).
5. Run visual match on an NGA visit artwork with a crop set.

## Related docs

- [DEPLOYMENT.md](DEPLOYMENT.md)
- [AI_RECOGNITION.md](AI_RECOGNITION.md)
- [storage/upload-storage.md](storage/upload-storage.md)
- [integrations/visual-matching.md](integrations/visual-matching.md)
