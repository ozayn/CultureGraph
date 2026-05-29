# CultureGraph

Minimal, mobile-first cultural exploration platform for museum visits, artwork annotation, and AI-assisted research.

**Full documentation:** [docs/README.md](docs/README.md)

## Stack

| Layer | Tech |
|-------|------|
| API | FastAPI, SQLAlchemy, Alembic, Pydantic |
| Web | Next.js (App Router), Tailwind, shadcn/ui, Konva |
| Database | PostgreSQL |

## Quick start

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
./scripts/dev.sh
```

- Web: http://localhost:3000  
- API: http://localhost:8000  
- API docs: http://localhost:8000/docs  

Existing Postgres: `./scripts/start.sh`

## Documentation

| Topic | Doc |
|-------|-----|
| **Index** | [docs/README.md](docs/README.md) |
| Architecture | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| AI / recognition | [docs/AI_RECOGNITION.md](docs/AI_RECOGNITION.md) |
| Deployment (Railway) | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) |
| Environment variables | [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md) |
| Admin tools | [docs/ADMIN_GUIDE.md](docs/ADMIN_GUIDE.md) |
| Visual matching | [docs/integrations/visual-matching.md](docs/integrations/visual-matching.md) |
| Upload storage | [docs/storage/upload-storage.md](docs/storage/upload-storage.md) |
| Testing | [docs/testing/testing.md](docs/testing/testing.md) |
| Roadmap | [docs/roadmap/roadmap.md](docs/roadmap/roadmap.md) |
| Design philosophy | [docs/product/design.md](docs/product/design.md) |

## Auth (summary)

- **Public:** browse visits, artworks, annotations, research notes
- **Admin:** Google Sign-In for emails in `ADMIN_EMAILS` — upload, annotate, enrich, match

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md#google-sign-in-on-deployed-urls) for OAuth setup.

## Testing (summary)

```bash
cd backend && source .venv/bin/activate && UPLOAD_DIR=uploads pytest
cd frontend && npm test
```

Details: [docs/testing/testing.md](docs/testing/testing.md)

## License

Private / unpublished — adjust as needed.
