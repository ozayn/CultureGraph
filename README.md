# CultureGraph

Minimal, mobile-first cultural exploration platform for museum visits, artwork annotation, and AI-assisted research.

## Stack

| Layer | Tech |
|-------|------|
| API | FastAPI, SQLAlchemy, Alembic, Pydantic |
| Web | Next.js (App Router), Tailwind, shadcn/ui, Konva |
| Database | PostgreSQL |

## Project layout

```
backend/          FastAPI API
frontend/         Next.js web app
scripts/dev.sh    Full local stack: Docker Postgres, migrate, seed, both servers
scripts/start.sh  Start API + web with env loading (no Docker)
DESIGN.md         Interaction philosophy, Story Mode notes, and product direction
```

## Environment files (local)

CultureGraph splits configuration by service. **Railway does not read the repo root `.env` file** — set variables on each Railway service instead (see below).

| File | Purpose |
|------|---------|
| [`backend/.env.example`](backend/.env.example) | API template → copy to `backend/.env` |
| [`frontend/.env.example`](frontend/.env.example) | Web template → copy to `frontend/.env.local` |
| [`.env.example`](.env.example) | Optional root convenience for local scripts only |

`scripts/start.sh` and `scripts/dev.sh` load env in this order (later files override earlier ones):

1. `.env` at repo root — **only if it exists** (optional)
2. `backend/.env` — API variables
3. `frontend/.env.local` — frontend variables

The script prints which files were found or missing; it never prints secret values.

### Local setup

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
# Edit backend/.env — add ANTHROPIC_API_KEY if using Claude research
```

**Backend only:** `DATABASE_URL`, `CORS_ORIGINS`, `ANTHROPIC_API_KEY`, `GOOGLE_CLIENT_ID`, `ADMIN_EMAILS`, `JWT_SECRET`, etc. belong in `backend/.env`.

**Frontend only:** `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SITE_URL`, `NEXT_PUBLIC_GOOGLE_CLIENT_ID`, `WEB_PORT` belong in `frontend/.env.local`.

Never put `ANTHROPIC_API_KEY`, `JWT_SECRET`, or `ADMIN_EMAILS` in the frontend env — they must stay on the API service.

## Public read / private write

CultureGraph is **public to browse** and **private to edit**:

- **Anyone** can view visits, artworks, annotations, and research notes without signing in.
- **Approved Google accounts** (listed in `ADMIN_EMAILS`) can create, edit, upload, import notes, annotate, and run AI research.

Local auth setup:

1. Create a [Google OAuth client](https://console.cloud.google.com/apis/credentials) (Web application).
2. Add **Authorized JavaScript origins** (exact origins, no trailing slash):
   - `http://localhost:3000`
   - `https://your-deployed-frontend-url` (Railway web service URL)
3. Set the same client ID on **both** services:
   - Backend: `GOOGLE_CLIENT_ID`
   - Frontend: `NEXT_PUBLIC_GOOGLE_CLIENT_ID`
4. Backend only:
   - `ADMIN_EMAILS=you@gmail.com` (comma-separated allowlist; use your exact Google email)
   - `JWT_SECRET` — long random secret
   - `CORS_ORIGINS=https://your-deployed-frontend-url` (and `http://localhost:3000` for local API)
5. Frontend only:
   - `NEXT_PUBLIC_API_URL=https://your-deployed-api-url` — must point to the **API** service, not the web app

Deployed sign-in flow: Google returns a credential → browser `POST`s to `${NEXT_PUBLIC_API_URL}/api/auth/google` → API verifies the Google token, checks `ADMIN_EMAILS`, issues an app JWT.

If sign-in hangs after Google, open DevTools → Network and confirm that POST status. Common fixes:
- `NEXT_PUBLIC_API_URL` pointing at the frontend URL instead of the API
- missing `CORS_ORIGINS` entry for the frontend origin
- `GOOGLE_CLIENT_ID` mismatch between frontend and backend
- your Google email missing from `ADMIN_EMAILS`

## Quick start (Docker)

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
./scripts/dev.sh
```

- Web: http://localhost:3000  
- API: http://localhost:8000  
- API docs: http://localhost:8000/docs  

## Quick start (existing Postgres)

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
./scripts/start.sh
```

## Regenerate PWA icons

```bash
cd frontend && npm run icons
```

## Testing

Backend tests **must not** run against your local development database (`culturegraph`). Pytest uses a separate Postgres database configured via `TEST_DATABASE_URL` (default: `culturegraph_test` on the same host as `DATABASE_URL`).

```bash
cd backend
source .venv/bin/activate
pytest
```

### One-time test database setup

**Docker (recommended):** `./scripts/dev.sh` creates `culturegraph_test` automatically when Docker Postgres is running. Fresh Docker volumes also get it from `docker/postgres/init-test-db.sql`.

**Local Postgres without Docker:** create the database once as a superuser:

```bash
psql -h localhost -d postgres -c "CREATE DATABASE culturegraph_test OWNER culturegraph;"
```

Set `TEST_DATABASE_URL` in `backend/.env` if you use a non-default name or host.

Each pytest run resets the test schema (`drop_all` / `create_all` at session start). Each test executes inside a transaction that is rolled back afterward, so test records never persist.

`backend/scripts/seed.py` seeds **development only** (Metropolitan Museum sample visit). It is not used by pytest.

Frontend unit tests (`cd frontend && npm test`) mock the API and do not write to Postgres.

### Cleaning accidental test records from dev

If pytest was previously pointed at the dev database, you may see visits like **Test Museum**, **Delete Museum**, or notes **Admin CRUD visit** in the local app. Remove them with:

```bash
./scripts/cleanup-test-data.sh
```

This deletes known pytest fixture names from `DATABASE_URL` in `backend/.env`. It does **not** touch `culturegraph_test`.

## Development notes

### Node `[DEP0205] module.register()` warning (harmless)

During `npm run dev` or `npm run build`, Node may print:

```text
(node:…) [DEP0205] DeprecationWarning: `module.register()` is deprecated. Use `module.registerHooks()` instead.
```

**Source:** Tailwind CSS v4 (`@tailwindcss/node`, pulled in by `@tailwindcss/postcss`), not CultureGraph app code, Next.js, tsx, or ts-node. With `--trace-deprecation`, the stack points at `frontend/node_modules/@tailwindcss/node/dist/index.js` (ESM cache loader registration).

**Impact:** Cosmetic only — CSS compiles and the app builds normally. No action required until Tailwind ships an update using `module.registerHooks()`.

To inspect the stack locally:

```bash
cd frontend
NODE_OPTIONS="--trace-deprecation" npm run build
```

## Railway deployment

Deploy as **two services** from this monorepo. Configure variables in each service’s **Railway dashboard** — not in a root `.env` file.

### API service

- **Root directory:** `backend/`
- Attach a **PostgreSQL** plugin; Railway injects `DATABASE_URL`.
- Railway sets `PORT`; the app reads it automatically.
- Release command runs Alembic migrations (see `backend/railway.toml`).

| Variable | Required | Notes |
|----------|----------|-------|
| `DATABASE_URL` | Yes | From Postgres plugin |
| `CORS_ORIGINS` | Yes | Your Railway web service URL |
| `GOOGLE_CLIENT_ID` | Yes | Same Web client ID as frontend |
| `ADMIN_EMAILS` | Yes | Comma-separated allowlist of editor emails |
| `JWT_SECRET` | Yes | Long random string for app JWT signing |
| `ANTHROPIC_API_KEY` | No | Enables Claude research; API service only |
| `ANTHROPIC_TIMEOUT_SECONDS` | No | Default `90`; museum-note import can take up to ~2 minutes end-to-end |
| `UPLOAD_DIR` | No | Default `uploads`; local folder served at `/uploads` |
| `UPLOAD_MAX_BYTES` | No | Default `10485760` (10 MB) for artwork photo uploads |

**Uploaded photos on Railway:** the API container filesystem is **ephemeral** unless you attach a volume. Without a volume, `/uploads/...` paths in the database survive redeploys but the files return **404**. Fix:

1. Add a Railway **volume** mounted at `/app/uploads` (or your service root + `uploads`).
2. Set `UPLOAD_DIR=/app/uploads` on the API service.
3. Re-upload photos or use **Find official image** to attach museum catalog URLs (these load from NGA/Smithsonian over HTTPS).

The API strips missing upload files from responses and falls back to `catalog_*` URLs when present, so the UI shows a clean placeholder instead of a broken image icon.

Do **not** set `NEXT_PUBLIC_*` variables on the API service.

### Web service

- **Root directory:** `frontend/`
- Node **≥20.12** (enforced via `package.json` engines and `frontend/nixpacks.toml`)
- Nixpacks runs `npm ci` and `npm run build`; do not duplicate those in Railway build settings
- Set `NEXT_PUBLIC_API_URL` to the public API URL **before** build/deploy.

| Variable | Required | Notes |
|----------|----------|-------|
| `NEXT_PUBLIC_API_URL` | Yes | Public API URL; web service only |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | Yes | Same OAuth client ID as backend |
| `NEXT_PUBLIC_SITE_URL` | No | Canonical URL for OpenGraph metadata |

Do **not** set `ANTHROPIC_API_KEY`, `JWT_SECRET`, or `ADMIN_EMAILS` on the Web service.

See `backend/Procfile`, `backend/railway.toml`, and `frontend/railway.toml` for start/build commands.

## Uploaded artwork images

### Current behavior

1. **Are uploads saved?** Yes. `POST /api/artworks/{id}/image` writes normalized files to disk and stores URLs on the artwork row.
2. **Local path:** `backend/uploads/artworks/{artwork_id}/{uuid}_display.webp` (plus `_master.webp` and `_thumb.webp` variants).
3. **Database:** `image_url` points at the web display copy; metadata columns store width, height, mime type, and file size.
4. **Railway redeploy:** The default `uploads/` folder is **ephemeral**. Redeploys/restarts wipe uploaded files unless you attach persistent storage.
5. **Validation:** JPEG/PNG/WebP only, max 10 MB, resized with Pillow (master 2000px, display 1600px, thumb 400px), metadata stripped, saved as WebP.

### Production storage recommendation

For Railway production, choose one of:

- **Railway Volume** mounted at `UPLOAD_DIR` (simplest path for the current filesystem-based API)
- **Object storage** (S3, Cloudflare R2, Supabase Storage) for durable media — recommended long term, but not wired in this repo yet

Until persistent storage is configured, treat uploaded artwork photos as **best-effort** on Railway.

## Features

- Log museum visits and attach artworks with photos
- Pin annotations on artwork images (Konva canvas)
- AI research drafts (Claude when configured, mock fallback otherwise)
- Mobile-first UX: bottom nav, sticky actions, 44px tap targets

## Manual QA checklist

### Manual annotation placement

1. Sign in with an approved Google account.
2. Open an artwork with a photo on **desktop** and **mobile**.
3. Tap **Annotate** (or **Add annotation** on desktop).
4. Confirm the banner reads **Tap image to place pin** (placement mode is active).
5. Tap the artwork image — the new-annotation sheet opens with coordinates saved.
6. Enter a note and tap **Save pin** — the pin appears on the canvas and in the list.
7. Tap an **existing pin** during placement mode — it must **not** open a second pin.
8. Scroll the page while placement mode is active — scrolling must **not** place a pin.
9. Tap **Cancel placement** — placement mode exits with no new pin.
10. Refresh the page — the pin stays in the same visual spot (0–100% of the image).
11. Use **Add text-only observation** (no image) or save without tapping — annotation saves with null coordinates and appears under **Annotations to place**.
12. Tap **Place on image** for that annotation, tap the image, confirm coordinates update after refresh.

### AI suggested annotation placement

1. Run **Research with AI** on an artwork with an image.
2. On a suggestion without a pin, tap **Place on image**.
3. On the annotate page, confirm the AI note appears in the placement banner.
4. Tap the image, save the annotation.
5. Return to research — the suggestion should no longer appear as pending.
6. Refresh — the pin remains; the suggestion stays accepted/hidden.

### Dev placement debug (local only)

With `npm run dev`, open the annotate page during placement mode. A **Placement debug** panel shows displayed image size, tap pixels, computed `x_percent` / `y_percent`, and the AI suggestion key when applicable.

### Auth

- Log out and confirm the annotate page shows **Sign in to add annotations.**

## Roadmap / future work

CultureGraph is intentionally small today. This list tracks what exists, what needs hardening, and what comes next.

### Shipped (baseline in repo)

| Area | Status | Notes |
|------|--------|--------|
| Admin database dashboard | Done | `/admin` — summary counts, tabbed tables, search, pagination; API at `/api/admin/*` |
| Image storage + normalization | Done (local) | Pillow pipeline, WebP variants, 10 MB limit; Railway needs a volume or object storage for durability |
| Cultural entity model (beyond artworks) | Done | `CulturalEntity` types (artist, concept, movement, etc.) saved separately from visit notes |
| Official artwork image lookup | Done | NGA + Smithsonian Open Access (SAAM, NPG, Hirshhorn, Asian Art, African Art); more museums later |

**Manual QA — official image lookup**

1. Create an artwork with no image (title + artist help matching).
2. Open artwork detail → tap **Find official image** in the placeholder.
3. For a **Smithsonian** visit (SAAM, Portrait Gallery, Hirshhorn, etc.), confirm candidates show Smithsonian museum attribution.
4. For an **NGA** visit, confirm National Gallery candidates.
5. Review candidate cards (thumbnail, title, artist, source, confidence).
6. Tap **Use this image** on a candidate.
7. Confirm the artwork shows the image and catalog attribution.
8. Refresh the page — image and metadata persist.
9. With an image present, **Replace image** opens the same lookup sheet.

### Next up

| Area | Goal |
|------|------|
| Visit detail redesign | Clearer grouping of artworks vs imported entities, lighter hierarchy, better scan on mobile |
| Better import review | Richer preview before save — edit entity type/name, merge duplicates, drop low-confidence rows |
| Search | Cross-visit search over museums, artworks, notes, entities (admin + public read paths) |
| Tags / themes | First-class tagging across visits and artworks; reuse entity themes beyond import-only fields |
| Graph-lite related entries | Surface `related_entities` and cross-links between visits, artworks, and concepts without a full graph DB |
| Mobile capture mode | Fast path: camera → artwork stub → optional pin → minimal fields; optimized for in-gallery use |

### Infrastructure follow-ups

- **Persistent image storage** on Railway (volume or S3/R2) — uploads are normalized but disk is ephemeral by default
- **Additional museum lookup sources** beyond NGA and Smithsonian (Met, Art Institute of Chicago, etc.)
- **Story Mode** — scene-by-scene artwork explainer (see [DESIGN.md](DESIGN.md))

## License

Private / unpublished — adjust as needed.
