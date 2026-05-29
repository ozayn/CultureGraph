# Architecture

CultureGraph is a monorepo with a **public-read / admin-write** web app, a FastAPI backend, and PostgreSQL.

## System diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser (Next.js)                                              │
│  - Public: visits, artworks, annotations, research notes        │
│  - Admin: upload, annotate, enrich, match, admin dashboard      │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS / JSON
                             │ Bearer JWT (admin only)
┌────────────────────────────▼────────────────────────────────────┐
│  FastAPI API (backend/)                                         │
│  Routers: visits, artworks, enrichment, research, admin, media  │
│  Services: lookup, visual matching, Claude, uploads, OCR        │
└─────┬──────────────────┬──────────────────┬─────────────────────┘
      │                  │                  │
      ▼                  ▼                  ▼
 PostgreSQL         Local filesystem    External APIs
 (metadata)         /uploads/...         Anthropic, OpenAI,
                                         SerpApi, museum open data
```

## Repository layout

| Path | Role |
|------|------|
| `backend/` | FastAPI app, Alembic migrations, scripts, tests |
| `frontend/` | Next.js App Router, Tailwind, shadcn/ui, Konva annotations |
| `scripts/` | `dev.sh`, `start.sh`, `migrate.sh`, cleanup helpers |
| `docs/` | This documentation tree |

## Core domains

### Visits and artworks

- A **visit** is a museum trip (museum name, city, date).
- An **artwork** belongs to a visit and holds user photos, crop region, catalog metadata, and enrichment state.
- **Annotations** are pin-based or text-only notes on an artwork image.

### Recognition (summary)

Recognition is **layered and optional** — see [AI_RECOGNITION.md](AI_RECOGNITION.md) for detail.

```
Photo upload → crop region → [manual tools + auto enrichment]
                │
                ├─ OpenCLIP visual match (NGA index)
                ├─ SerpApi web lens (optional)
                ├─ Text museum lookup (NGA, Smithsonian, Met, AIC, Wikimedia)
                └─ Claude vision → lookup → identification calibration
```

Nothing applies catalog metadata automatically. Admins review candidates and `PUT` artwork fields.

### Auth model

| Audience | Access |
|----------|--------|
| Public | Read visits, artworks, annotations, research notes |
| Admin (`ADMIN_EMAILS`) | Google Sign-In → app JWT → create/edit/upload/enrich |

Google OAuth verifies identity; the API issues its own JWT. Secrets never go to the frontend build.

### Data persistence

| Data | Storage |
|------|---------|
| Relational records | PostgreSQL (`visits`, `artworks`, `annotations`, `research_notes`, `cultural_entities`, `collection_*`) |
| User uploads | Filesystem under `UPLOAD_DIR` (volume on Railway) |
| NGA visual index | `collection_artworks` + `collection_image_embeddings` |
| Museum text indexes | JSON files in `backend/app/data/` (built offline) |
| Enrichment snapshot | `artworks.enrichment_lookup` JSON |
| Match/lens results | **Ephemeral** — API response only until user applies |

### Background work

- **Enrichment** runs in a background thread/async task after label upload or crop change (or manual POST).
- **NGA visual index build** is an offline admin script, not part of deploy.
- No separate worker service in MVP.

## Request flows

### Artwork capture

```
POST /api/artworks/{id}/image
  → Pillow normalize → WebP master/display/thumb
  → PATCH /image-region (optional crop)
  → triggers enrichment if label present or region changes
```

### Auto enrichment

```
POST /api/artworks/{id}/enrichment
  → Claude vision (+ optional label image)
  → build_retrieval_lookup_query
  → lookup_artwork_candidates (semantic/fuzzy stages)
  → build_identification + calibrate draft
  → research_notes row + artworks.enrichment_lookup cache
```

### Manual recognition tools (admin)

| Endpoint | Purpose |
|----------|---------|
| `POST .../visual-match` | OpenCLIP vs NGA embedding index |
| `POST .../lens-search` | SerpApi Google Lens web fallback |
| `GET .../lookup-image` | Text catalog search |
| `POST .../research` | Claude-only research (no lookup) |

## Frontend architecture

- **App Router** pages under `frontend/src/app/`
- **Artwork detail** orchestrates enrichment panel, image lookup sheet, annotation canvas
- **Admin dashboard** at `/admin` — DB browser + health cards
- **API client** (`lib/api.ts`) attaches JWT; long timeouts for enrichment/upload

## Design principles

1. **Human-in-the-loop** — AI suggests; humans apply.
2. **Museum-scoped first** — visit museum name routes lookup and visual match scope.
3. **Graceful degradation** — mock LLM, empty visual index, missing API keys → clear notices.
4. **Mobile-first** — bottom sheets, 44px targets, fit-to-width images.

See [product/design.md](product/design.md) for interaction philosophy.

## Related docs

- [AI_RECOGNITION.md](AI_RECOGNITION.md)
- [DEPLOYMENT.md](DEPLOYMENT.md)
- [storage/upload-storage.md](storage/upload-storage.md)
- [ENVIRONMENT.md](ENVIRONMENT.md)
