# Web visual search (SerpApi Google Lens)

CultureGraph can optionally fall back to **web visual search** when the local museum visual index is empty or museum matches are weak. This is an admin-only feature powered by [SerpApi's Google Lens API](https://serpapi.com/google-lens-api).

This is **not** an official Google Lens API. SerpApi scrapes Google Lens result pages and returns structured JSON.

## Setup

1. Create a SerpApi account and copy your API key.
2. Set on the **API server only** (never on the frontend):

```bash
SERPAPI_API_KEY=your-key
```

3. For uploaded `/uploads/...` photos, SerpApi must fetch the image from a **public URL**. Set your deployed API origin:

```bash
PUBLIC_API_BASE_URL=https://your-api.up.railway.app
```

Local development with uploads requires a tunnel (for example ngrok) pointing at the API, or testing with an artwork that already has an `https://` catalog image URL.

Optional tuning:

| Variable | Default | Purpose |
|----------|---------|---------|
| `SERPAPI_TIMEOUT_SECONDS` | `45` | Upstream request timeout |
| `LENS_SEARCH_MAX_RESULTS` | `12` | Max candidates returned |

## API

`POST /api/artworks/{id}/lens-search` (admin JWT required)

Uses the artwork's current `image_url` (typically the cropped display image).

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

- `provider` — always `"Web visual search"`
- `disclaimer` — third-party notice
- `notice` — empty-result or configuration hints

The API key is never exposed to the browser.

## Frontend

On the artwork AI assistant panel, admins with a cropped photo can click **Try web visual search**. Results appear in a separate section below museum visual matches. Nothing is auto-applied; the user must review and choose **Use image** or **Use image + title** per candidate.

## Security and scope

- Admin-only (`require_admin_user`)
- Optional — if `SERPAPI_API_KEY` is unset, the endpoint returns a clear configuration error
- Third-party dependency with usage-based billing on SerpApi
- Results may include shopping or unrelated pages; always review before applying metadata

## Related docs

- Local museum visual matching: `docs/VISUAL_MATCHING.md`
