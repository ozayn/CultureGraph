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
backend/          FastAPI API (canonical source)
frontend/         Next.js web app (canonical source)
apps/api/         Symlink → backend/
apps/web/         Symlink → frontend/
scripts/dev.sh    Full local stack: Docker Postgres, migrate, seed, both servers
scripts/start.sh  Start API + web with env loading (no Docker)
DESIGN.md         Interaction philosophy and future Story Mode notes
```

## Environment files (local)

CultureGraph splits configuration by service. **Railway does not read the repo root `.env` file** — set variables on each Railway service instead (see below).

| File | Purpose |
|------|---------|
| [`apps/api/.env.example`](apps/api/.env.example) | API template → copy to `apps/api/.env` |
| [`apps/web/.env.example`](apps/web/.env.example) | Web template → copy to `apps/web/.env.local` |
| [`.env.example`](.env.example) | Optional root convenience for local scripts only |

`scripts/start.sh` and `scripts/dev.sh` load env in this order (later files override earlier ones):

1. `.env` at repo root — **only if it exists** (optional)
2. `apps/api/.env` — backend/API variables
3. `apps/web/.env.local` — frontend variables

The script prints which files were found or missing; it never prints secret values.

### Local setup

```bash
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env.local
# Edit apps/api/.env — add ANTHROPIC_API_KEY if using Claude research
```

**API-only:** `DATABASE_URL`, `CORS_ORIGINS`, `ANTHROPIC_API_KEY`, etc. belong in `apps/api/.env`.

**Web-only:** `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SITE_URL`, `WEB_PORT` belong in `apps/web/.env.local`.

Never put `ANTHROPIC_API_KEY` in the web env — it must stay on the API service.

## Quick start (Docker)

```bash
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env.local
./scripts/dev.sh
```

- Web: http://localhost:3000  
- API: http://localhost:8000  
- API docs: http://localhost:8000/docs  

## Quick start (existing Postgres)

```bash
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env.local
./scripts/start.sh
```

## Regenerate PWA icons

```bash
cd apps/web && npm run icons
```

## Railway deployment

Deploy as **two services** from this monorepo. Configure variables in each service’s **Railway dashboard** — not in a root `.env` file.

### API service

- **Root directory:** `backend/` (or `apps/api/`)
- Attach a **PostgreSQL** plugin; Railway injects `DATABASE_URL`.
- Railway sets `PORT`; the app reads it automatically.
- Release command runs Alembic migrations (see `backend/railway.toml`).

| Variable | Required | Notes |
|----------|----------|-------|
| `DATABASE_URL` | Yes | From Postgres plugin |
| `CORS_ORIGINS` | Yes | Your Railway web service URL |
| `ANTHROPIC_API_KEY` | No | Enables Claude research; API service only |
| `UPLOAD_DIR` | No | Default `uploads` |

Do **not** set `NEXT_PUBLIC_*` variables on the API service.

### Web service

- **Root directory:** `frontend/` (or `apps/web/`)
- Set `NEXT_PUBLIC_API_URL` to the public API URL **before** build/deploy.

| Variable | Required | Notes |
|----------|----------|-------|
| `NEXT_PUBLIC_API_URL` | Yes | Public API URL; web service only |
| `NEXT_PUBLIC_SITE_URL` | No | Canonical URL for OpenGraph metadata |

Do **not** set `ANTHROPIC_API_KEY` on the Web service.

See `backend/Procfile`, `backend/railway.toml`, and `frontend/railway.toml` for start/build commands.

## Features

- Log museum visits and attach artworks with photos
- Pin annotations on artwork images (Konva canvas)
- AI research drafts (Claude when configured, mock fallback otherwise)
- Mobile-first UX: bottom nav, sticky actions, 44px tap targets

## License

Private / unpublished — adjust as needed.
