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
DESIGN.md         Interaction philosophy and future Story Mode notes
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

### Artwork annotations

1. Sign in with an approved Google account.
2. Create or open an artwork with a photo attached.
3. Open **Annotate** from the artwork detail page.
4. Click or tap the image — the new annotation sheet should open.
5. Choose a category, enter a note, and tap **Save pin**.
6. Confirm the pin appears immediately on the canvas and in the list below.
7. Refresh the page — the pin should still be there.
8. Log out and confirm the annotate page shows **Sign in to add annotations.**

## License

Private / unpublished — adjust as needed.
