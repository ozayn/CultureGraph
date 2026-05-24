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
2. Add authorized JavaScript origins: `http://localhost:3000` (and your Railway web URL in production).
3. Set the same client ID on **both** services:
   - Backend: `GOOGLE_CLIENT_ID`
   - Frontend: `NEXT_PUBLIC_GOOGLE_CLIENT_ID`
4. Backend only: set `ADMIN_EMAILS=you@gmail.com` (comma-separated allowlist) and a long random `JWT_SECRET`.

Sign in uses Google ID tokens verified server-side; the API returns an app JWT stored in `localStorage`. All write endpoints require `Authorization: Bearer …`.

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
| `UPLOAD_DIR` | No | Default `uploads` |

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

## Features

- Log museum visits and attach artworks with photos
- Pin annotations on artwork images (Konva canvas)
- AI research drafts (Claude when configured, mock fallback otherwise)
- Mobile-first UX: bottom nav, sticky actions, 44px tap targets

## License

Private / unpublished — adjust as needed.
