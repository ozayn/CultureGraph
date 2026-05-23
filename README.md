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
backend/          FastAPI API (also linked as apps/api/)
frontend/         Next.js web app (also linked as apps/web/)
scripts/dev.sh    Full local stack: Docker Postgres, migrate, seed, both servers
scripts/start.sh  Start API + web with env loading (no Docker)
DESIGN.md         Interaction philosophy and future Story Mode notes
```

## Quick start (Docker)

```bash
cp .env.example .env
./scripts/dev.sh
```

- Web: http://localhost:3000  
- API: http://localhost:8000  
- API docs: http://localhost:8000/docs  

## Quick start (existing Postgres)

```bash
cp .env.example .env
cp backend/.env.example backend/.env   # optional per-service overrides
./scripts/start.sh
```

`start.sh` loads `.env`, `backend/.env`, and `frontend/.env.local`, runs migrations, then starts uvicorn on port **8000** and Next.js on port **3000**.

## Environment variables

See [`.env.example`](.env.example) for the full list. Key values:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string |
| `API_PORT` | FastAPI port (default 8000) |
| `NEXT_PUBLIC_API_URL` | Browser-facing API URL |
| `CORS_ORIGINS` | Allowed web origins for the API |
| `NEXT_PUBLIC_SITE_URL` | Canonical site URL for OpenGraph metadata |

## Regenerate PWA icons

```bash
cd frontend && npm run icons
```

## Railway deployment

Deploy as **two services** from this monorepo:

### API service

- **Root directory:** `backend/` (or `apps/api/`)
- Attach a **PostgreSQL** plugin; `DATABASE_URL` is injected automatically.
- Railway sets `PORT`; the app reads it via config.
- Release command runs Alembic migrations (see `backend/railway.toml`).
- Set `CORS_ORIGINS` to your web service URL.

### Web service

- **Root directory:** `frontend/` (or `apps/web/`)
- Set `NEXT_PUBLIC_API_URL` to the public API URL **before** build.
- Optionally set `NEXT_PUBLIC_SITE_URL` for OpenGraph links.

See `backend/Procfile`, `backend/railway.toml`, and `frontend/railway.toml` for start/build commands.

## Features

- Log museum visits and attach artworks with photos
- Pin annotations on artwork images (Konva canvas)
- Generate mocked AI research drafts per artwork
- Mobile-first UX: bottom nav, sticky actions, 44px tap targets

## License

Private / unpublished — adjust as needed.
