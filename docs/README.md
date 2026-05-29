# CultureGraph documentation

CultureGraph is a mobile-first platform for museum visits, artwork annotation, and AI-assisted research. This folder is the canonical home for setup, architecture, and operations docs.

## Documentation map

| Category | Documents |
|----------|-----------|
| **Getting started** | [Root README](../README.md) — quick start, stack overview |
| **Architecture** | [ARCHITECTURE.md](ARCHITECTURE.md) |
| **AI / recognition** | [AI_RECOGNITION.md](AI_RECOGNITION.md), [ai/audio-notes.md](ai/audio-notes.md) |
| **Integrations** | [integrations/museum-lookup.md](integrations/museum-lookup.md), [integrations/visual-matching.md](integrations/visual-matching.md), [integrations/lens-search.md](integrations/lens-search.md) |
| **Deployment** | [DEPLOYMENT.md](DEPLOYMENT.md), [ENVIRONMENT.md](ENVIRONMENT.md) |
| **Storage** | [storage/upload-storage.md](storage/upload-storage.md) |
| **Admin tools** | [ADMIN_GUIDE.md](ADMIN_GUIDE.md) |
| **Testing** | [testing/testing.md](testing/testing.md) |
| **Product / UX** | [product/design.md](product/design.md) |
| **Roadmap** | [roadmap/roadmap.md](roadmap/roadmap.md) |

## Recommended reading order

1. [Root README](../README.md) — run the app locally
2. [ARCHITECTURE.md](ARCHITECTURE.md) — how the pieces fit together
3. [AI_RECOGNITION.md](AI_RECOGNITION.md) — recognition pipeline and human-in-the-loop design
4. [DEPLOYMENT.md](DEPLOYMENT.md) — Railway two-service deploy
5. [ENVIRONMENT.md](ENVIRONMENT.md) — all environment variables

## Directory layout

```
docs/
  README.md                 ← you are here
  ARCHITECTURE.md
  AI_RECOGNITION.md
  DEPLOYMENT.md
  ADMIN_GUIDE.md
  ENVIRONMENT.md
  ai/                       Audio notes, future OCR docs
  integrations/             Museum APIs, visual index, web lens
  storage/                  Uploads and persistence
  testing/                  Pytest and QA
  roadmap/                  Planned work
  product/                  Interaction philosophy
```

## API reference

Interactive OpenAPI docs are served at `/docs` when the API is running (local: http://localhost:8000/docs).
