# Testing

## Backend (pytest)

Tests **must not** use the development database. Pytest connects to `TEST_DATABASE_URL` (default: `culturegraph_test`).

```bash
cd backend
source .venv/bin/activate
UPLOAD_DIR=uploads pytest
```

### One-time test database

**Docker:** `./scripts/dev.sh` creates `culturegraph_test` automatically.

**Local Postgres:**

```bash
psql -h localhost -d postgres -c "CREATE DATABASE culturegraph_test OWNER culturegraph;"
```

### Isolation model

- Session start: `drop_all` / `create_all`
- Each test: nested transaction rolled back
- API tests override `get_db` to the same connection

### Visual matching tests

Use mock embeddings — no OpenCLIP install required:

```bash
export VISUAL_EMBEDDING_BACKEND=test
```

(conftest sets this by default)

### Common local issue

If `UPLOAD_DIR=/app/uploads` in `backend/.env`, tests may fail on macOS (read-only `/app`). Use `UPLOAD_DIR=uploads` locally.

## Frontend (Vitest)

```bash
cd frontend
npm test
```

Unit tests mock the API; no Postgres writes.

## Manual QA

The root [README](../README.md) includes checklists for:

- Annotation placement (desktop + mobile)
- AI suggested annotation placement
- Official image lookup
- Auth flows

## Cleaning test data from dev DB

If pytest previously targeted the dev database:

```bash
./scripts/cleanup-test-data.sh
```

Deletes known fixture names (e.g. “Test Museum”) from `DATABASE_URL`. Does not touch `culturegraph_test`.

## Related docs

- [DEPLOYMENT.md](../DEPLOYMENT.md)
- [ENVIRONMENT.md](../ENVIRONMENT.md)
