# Environment variables

CultureGraph splits configuration by service. **Never put API secrets in the frontend.**

Templates:

- [`backend/.env.example`](../backend/.env.example) → `backend/.env`
- [`frontend/.env.example`](../frontend/.env.example) → `frontend/.env.local`

`scripts/start.sh` and `scripts/dev.sh` load: root `.env` (optional) → `backend/.env` → `frontend/.env.local`.

## Quick reference

### API service only

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | local postgres URL | PostgreSQL connection |
| `TEST_DATABASE_URL` | `.../culturegraph_test` | Pytest database (local only) |
| `API_HOST` | `0.0.0.0` | Bind address |
| `API_PORT` / `PORT` | `8000` | Listen port (Railway sets `PORT`) |
| `APP_ENV` | `development` | `production` enables stricter upload warnings |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed browser origins |

### Google auth (API)

| Variable | Required | Purpose |
|----------|----------|---------|
| `GOOGLE_CLIENT_ID` | Prod | Google OAuth client ID |
| `ADMIN_EMAILS` | Prod | Comma-separated editor allowlist |
| `JWT_SECRET` | Prod | App JWT signing secret |
| `JWT_EXPIRATION_DAYS` | `7` | Token lifetime |

### Anthropic (Claude)

| Variable | Default | Purpose |
|----------|---------|---------|
| `ANTHROPIC_API_KEY` | — | Research, enrichment, label OCR |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Model name |
| `ANTHROPIC_TIMEOUT_SECONDS` | `120` | Request timeout |
| `ANTHROPIC_MAX_TOKENS` | `2048` | Max response tokens |

Used for: artwork enrichment, standalone research, wall-label OCR.

### OpenAI (audio)

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPENAI_API_KEY` | — | Whisper transcription |
| `OPENAI_TRANSCRIPTION_MODEL` | `whisper-1` | Transcription model |
| `AUDIO_NOTE_MAX_BYTES` | `26214400` (25 MB) | Upload limit |
| `AUDIO_NOTE_MAX_DURATION_SECONDS` | `300` | Max recording length |

See [ai/audio-notes.md](ai/audio-notes.md).

### SerpApi (web visual search)

| Variable | Default | Purpose |
|----------|---------|---------|
| `SERPAPI_API_KEY` | — | Google Lens via SerpApi |
| `PUBLIC_API_BASE_URL` | — | Public API origin for `/uploads/` image URLs |
| `SERPAPI_TIMEOUT_SECONDS` | `45` | Upstream timeout |
| `LENS_SEARCH_MAX_RESULTS` | `12` | Max candidates returned |

See [integrations/lens-search.md](integrations/lens-search.md).

### Upload storage

| Variable | Default | Purpose |
|----------|---------|---------|
| `UPLOAD_DIR` | `uploads` | Filesystem root for uploads |
| `UPLOAD_STORAGE_BACKEND` | `filesystem` | `filesystem` (s3/r2 planned) |
| `UPLOAD_MAX_BYTES` | `10485760` (10 MB) | Artwork photo limit |

Railway production: `UPLOAD_DIR=/app/uploads` with a mounted volume.

See [storage/upload-storage.md](storage/upload-storage.md).

### Visual matching / NGA index

| Variable | Default | Purpose |
|----------|---------|---------|
| `VISUAL_EMBEDDING_BACKEND` | `openclip` | `openclip` or `test` (pytest) |
| `VISUAL_EMBEDDING_MODEL` | `ViT-B-32` | OpenCLIP architecture |
| `VISUAL_EMBEDDING_PRETRAINED` | `openai` | Weight tag |
| `NGA_INDEX_LIMIT` | `2000` | Default CLI `--limit` for index build |
| `VISUAL_MATCH_TOP_K` | `12` | Candidates returned to UI |
| `VISUAL_MATCH_HIGH_THRESHOLD` | `0.82` | “high” confidence cutoff |
| `VISUAL_MATCH_POSSIBLE_THRESHOLD` | `0.68` | “possible” confidence cutoff |

See [integrations/visual-matching.md](integrations/visual-matching.md).

### Frontend only

| Variable | Purpose |
|----------|---------|
| `NEXT_PUBLIC_API_URL` | Browser → API base URL (**required** at build on Railway) |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | Google Sign-In (must match backend) |
| `NEXT_PUBLIC_SITE_URL` | Canonical site URL for metadata |
| `WEB_PORT` | Local dev port (`scripts/start.sh`) |

## Railway checklist

| Service | Set | Do not set |
|---------|-----|------------|
| API | `DATABASE_URL`, `JWT_SECRET`, `ADMIN_EMAILS`, `GOOGLE_CLIENT_ID`, `CORS_ORIGINS`, `ANTHROPIC_API_KEY`, `UPLOAD_DIR`, optional `SERPAPI_*`, `OPENAI_*` | `NEXT_PUBLIC_*` |
| Web | `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | `ANTHROPIC_API_KEY`, `JWT_SECRET`, `SERPAPI_API_KEY` |

## Related docs

- [ENVIRONMENT.md](ENVIRONMENT.md)
- [DEPLOYMENT.md](DEPLOYMENT.md)
