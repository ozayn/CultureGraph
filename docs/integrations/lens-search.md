# Web visual search (Google Lens providers)

CultureGraph can optionally fall back to **web visual search** when the local museum visual index is empty or museum matches are weak. This is an admin-only feature backed by a pluggable provider:

| Provider | Engine | Docs |
|----------|--------|------|
| **SerpApi** (default) | Google Lens via SerpApi | [SerpApi Google Lens API](https://serpapi.com/google-lens-api) |
| **SearchAPI** | Google Lens via SearchAPI.io | [SearchAPI Google Lens](https://www.searchapi.io/docs/google-lens) |

Neither provider is an official Google Lens API. Both scrape or proxy Google Lens result pages and return structured JSON (`visual_matches`, `exact_matches`).

## Provider setup

Set on the **API server only** (never on the frontend):

```bash
# serpapi (default) or searchapi
WEB_VISUAL_SEARCH_PROVIDER=serpapi

# SerpApi
SERPAPI_API_KEY=your-serpapi-key

# SearchAPI.io (alternative)
SEARCHAPI_API_KEY=your-searchapi-key
```

Only configure the API key for the provider you select. If `WEB_VISUAL_SEARCH_PROVIDER=searchapi` but `SEARCHAPI_API_KEY` is unset, the endpoint returns a clear configuration error (and vice versa for SerpApi).

For uploaded `/uploads/...` photos, the provider must fetch the image from a **public HTTPS URL**. Set your deployed API origin:

```bash
PUBLIC_API_BASE_URL=https://your-api.up.railway.app
```

Local development with uploads requires a tunnel (for example ngrok) pointing at the API, or testing with an artwork that already has an `https://` catalog image URL.

Optional tuning:

| Variable | Default | Purpose |
|----------|---------|---------|
| `WEB_VISUAL_SEARCH_PROVIDER` | `serpapi` | Active provider (`serpapi` or `searchapi`) |
| `SERPAPI_TIMEOUT_SECONDS` | `45` | Upstream request timeout (both providers) |
| `LENS_SEARCH_MAX_RESULTS` | `12` | Max candidates returned |

SearchAPI accepts `api_key` as a query parameter (used by CultureGraph) or `Authorization: Bearer <key>`.

## Crop behavior

Artworks store crop coordinates as percentages of the original upload (`crop_x_percent`, `crop_y_percent`, `crop_width_percent`, `crop_height_percent`). The display `image_url` is already cropped for the UI.

| Provider | Image sent | Crop parameter |
|----------|------------|----------------|
| **SerpApi** | Display `image_url` (pre-cropped) | Not sent |
| **SearchAPI** | Master `image_master_url` when a crop exists, otherwise display URL | `crop=left;top;right;bottom` with normalized `0–1` coordinates (`left;top;right;bottom`) |

Example: crop at 10%, 20% with size 50%×40% → `crop=0.1000;0.2000;0.6000;0.6000`.

If crop metadata exists but `image_master_url` is missing, SearchAPI falls back to the display image without a crop parameter.

## API

`POST /api/artworks/{id}/lens-search` (admin JWT required)

Response fields per candidate:

- `title`
- `source` (site label)
- `source_url`
- `thumbnail_url`
- `image_url`
- `snippet`
- `source_rank`
- `confidence_label` (`high`, `possible`, `weak`)

Top-level response:

- `provider` — provider badge, e.g. `"Web visual search (SearchAPI)"` or `"Web visual search (SerpApi)"`
- `disclaimer` — third-party notice
- `notice` — empty-result or configuration hints
- `query_image_url` — public image URL sent to the provider

The API key is never exposed to the browser. Server logs redact `api_key`, `key`, `token`, and Bearer tokens.

## Provider differences

| | SerpApi | SearchAPI |
|---|---------|-----------|
| **Base URL** | `https://serpapi.com/search.json` | `https://www.searchapi.io/api/v1/search` |
| **Auth** | `api_key` query param | `api_key` query param or Bearer header |
| **Crop support** | No (uses pre-cropped display image) | Yes (`crop` on master image) |
| **Match sections** | `visual_matches`, `exact_matches` | `visual_matches`, `exact_matches` |
| **Billing** | SerpApi usage | SearchAPI.io usage |

Both providers are normalized into the same response shape. `exact_matches` are merged with `visual_matches` (deduplicated by link/image/title).

## Frontend

On the artwork AI assistant panel, admins with a photo can click **Try web visual search**. Results appear in a separate section below museum visual matches with a provider badge (for example **Web visual search (SearchAPI)**). Nothing is auto-applied; the user must review and choose **Use image** or **Use image + title** per candidate.

## Security and scope

- Admin-only (`require_admin_user`)
- Optional — misconfiguration returns a clear error
- Third-party dependency with usage-based billing
- Results may include shopping or unrelated pages; always review before applying metadata

## Troubleshooting

Common `400` responses from `POST /api/artworks/{id}/lens-search`:

| Error theme | Likely cause | Fix |
|-------------|--------------|-----|
| `PUBLIC_API_BASE_URL` | Upload path but no public API origin configured | Set `PUBLIC_API_BASE_URL` to your deployed API HTTPS origin |
| `not publicly reachable` | Image 404 at the public origin | Upload exists only locally, or wrong `PUBLIC_API_BASE_URL`; deploy uploads or use a tunnel (ngrok) |
| `non-public host` | `PUBLIC_API_BASE_URL` is `localhost` | Providers cannot fetch localhost; use a public HTTPS origin |
| `SEARCHAPI_API_KEY` / `SERPAPI_API_KEY` | Missing or wrong provider key | Set the key for the active `WEB_VISUAL_SEARCH_PROVIDER` |
| `not authorized` | Invalid provider API key | Verify the key in the provider dashboard |

Server logs include safe debug fields: `provider`, `artwork_id`, `has_image_url`, `has_master_url`, `public_url_host`, `has_crop`, and redacted provider errors.

## Related docs

- Local museum visual matching: [visual-matching.md](visual-matching.md)
- Environment variables: [../ENVIRONMENT.md](../ENVIRONMENT.md)
