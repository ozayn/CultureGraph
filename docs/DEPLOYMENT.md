# Deployment

CultureGraph deploys to **Railway** as two services from one monorepo: API (`backend/`) and Web (`frontend/`). Configure variables in each service’s Railway dashboard — not in a repo root `.env`.

## Architecture on Railway

```
┌─────────────────────┐     ┌─────────────────────┐
│  Web service        │     │  API service        │
│  frontend/          │────▶│  backend/           │
│  Next.js            │     │  FastAPI            │
│  NEXT_PUBLIC_*      │     │  Secrets, uploads   │
└─────────────────────┘     └──────────┬──────────┘
                                       │
                            ┌──────────▼──────────┐
                            │  PostgreSQL plugin  │
                            └─────────────────────┘
                                       │
                            ┌──────────▼──────────┐
                            │  Volume (optional)  │
                            │  /app/uploads       │
                            └─────────────────────┘
```

## API service

| Setting | Value |
|---------|-------|
| Root directory | `backend/` |
| Start | See `backend/Procfile`, `backend/railway.toml` |
| Release command | `alembic upgrade head` (in `railway.toml`) |
| Port | Railway sets `PORT`; app reads via `API_PORT` alias |

### Required variables

| Variable | Notes |
|----------|-------|
| `DATABASE_URL` | From Postgres plugin |
| `CORS_ORIGINS` | Exact frontend origin(s), comma-separated |
| `GOOGLE_CLIENT_ID` | Must match frontend `NEXT_PUBLIC_GOOGLE_CLIENT_ID` |
| `ADMIN_EMAILS` | Comma-separated editor allowlist |
| `JWT_SECRET` | Long random string |

### Recommended for production

| Variable | Notes |
|----------|-------|
| `APP_ENV` | `production` |
| `UPLOAD_DIR` | `/app/uploads` with mounted volume |
| `ANTHROPIC_API_KEY` | Claude research/enrichment |
| `PUBLIC_API_BASE_URL` | Public API URL (for SerpApi lens on uploads) |

### Optional features

| Variable | Feature |
|----------|---------|
| `OPENAI_API_KEY` | Audio note Whisper transcription |
| `SERPAPI_API_KEY` | Web visual search fallback |
| `VISUAL_EMBEDDING_BACKEND` | `openclip` if running visual match in API container |

Do **not** set `NEXT_PUBLIC_*` on the API service.

### Upload persistence

Railway containers use **ephemeral disk** by default. Without a volume, uploaded images and audio are lost on redeploy.

1. Attach a **volume** at `/app/uploads`
2. Set `UPLOAD_DIR=/app/uploads`
3. Verify `GET /api/admin/upload-health` → `persistent: true`

Details: [storage/upload-storage.md](storage/upload-storage.md).

### Visual index on Railway

Do **not** run full NGA indexing on every deploy. Build the index locally or as a one-off job, then rely on Postgres embeddings. See [integrations/visual-matching.md](integrations/visual-matching.md).

## Web service

| Setting | Value |
|---------|-------|
| Root directory | `frontend/` |
| Node | ≥20.12 (`package.json` engines, `nixpacks.toml`) |
| Build | `npm ci` + `npm run build` (via Nixpacks) |

### Required variables

| Variable | Notes |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | Public **API** URL — set **before** build |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | Same as backend `GOOGLE_CLIENT_ID` |

### Optional

| Variable | Notes |
|----------|-------|
| `NEXT_PUBLIC_SITE_URL` | Canonical URL for OpenGraph |

Do **not** set `ANTHROPIC_API_KEY`, `JWT_SECRET`, or `ADMIN_EMAILS` on the Web service.

## Google Sign-In on deployed URLs

1. Google Cloud Console → OAuth client → **Authorized JavaScript origins**:
   - `https://your-web-service.up.railway.app`
   - `http://localhost:3000` (local)
2. Same client ID on both Railway services.
3. `CORS_ORIGINS` must include the web origin exactly.

If sign-in hangs after Google, check DevTools → Network for `POST /api/auth/google` and verify `NEXT_PUBLIC_API_URL` points at the API, not the web app.

## Local development

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
./scripts/dev.sh    # Docker Postgres + migrate + seed + both servers
# or
./scripts/start.sh  # existing Postgres
```

- Web: http://localhost:3000
- API: http://localhost:8000
- API docs: http://localhost:8000/docs

## Migrations

```bash
./scripts/migrate.sh
```

Use the backend virtualenv (Python 3.11+). `dev.sh` runs migrations on startup.

## PWA icons

```bash
cd frontend && npm run icons
```

## Related docs

- [ENVIRONMENT.md](ENVIRONMENT.md) — full variable reference
- [storage/upload-storage.md](storage/upload-storage.md)
- [ADMIN_GUIDE.md](ADMIN_GUIDE.md) — post-deploy health checks
