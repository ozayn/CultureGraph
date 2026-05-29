# Roadmap and future work

CultureGraph is intentionally small today. This page tracks shipped baseline, known gaps, and planned direction.

## Shipped baseline

| Area | Status | Notes |
|------|--------|-------|
| Visits, artworks, annotations | Done | Mobile-first, Konva pins |
| Google admin auth | Done | Public read / admin write |
| Claude research + enrichment | Done | Vision, lookup, identification |
| Museum text lookup | Done | NGA, Smithsonian, Met, AIC, Wikimedia |
| NGA visual index (OpenCLIP) | Done | Offline build, manual visual match |
| SerpApi web lens fallback | Done | Admin-only optional |
| Audio notes | Done | Whisper + Claude interpretation, EN/FA |
| Admin dashboard | Done | CRUD browser, upload + index health |
| Persistent upload docs | Done | Railway volume guide |

## Known limitations

See [AI_RECOGNITION.md](../AI_RECOGNITION.md#known-limitations). Summary:

- Image-only recognition without OCR remains weak
- Visual index is **NGA-first** only
- Railway uploads need a volume or object storage
- SerpApi needs publicly reachable image URLs
- Recognition tools are not unified into one ranker

## Next up (product)

| Area | Goal |
|------|------|
| Visit detail redesign | Clearer artwork vs entity grouping on mobile |
| Import review | Richer preview, merge duplicates, edit entity types |
| Cross-visit search | Museums, artworks, notes, entities |
| Tags / themes | First-class tagging across visits |
| Graph-lite links | Surface `related_entities` without a graph DB |
| Mobile capture mode | Camera → stub → optional pin, in-gallery speed |

## Infrastructure

| Area | Goal |
|------|------|
| Persistent object storage | S3 / R2 adapter (interface exists) |
| Additional visual indexes | Smithsonian, Met, AIC embeddings |
| pgvector | Replace JSON embedding scan at scale |
| Background index jobs | Progress API for long NGA builds |
| Google Cloud Vision | Label OCR complement (see architecture audit) |

## Recognition / AI

| Area | Goal |
|------|------|
| Fuse visual match into enrichment | When text lookup empty, auto-suggest OpenCLIP hits |
| Label OCR improvements | Dedicated GCP Vision or stronger parsing |
| Multilingual research | Expand beyond audio notes EN/FA |
| Candidate explanation | AI summary only after user picks a match |

## UX / product

| Area | Goal |
|------|------|
| Story Mode | Scene-by-scene artwork explainer ([product/design.md](../product/design.md)) |
| Stronger annotation flows | Batch place AI suggestions |

## Related docs

- [product/design.md](../product/design.md)
- [AI_RECOGNITION.md](../AI_RECOGNITION.md)
- [ARCHITECTURE.md](../ARCHITECTURE.md)
