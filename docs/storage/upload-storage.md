# Persistent upload storage

CultureGraph stores artwork photos, label images, and audio notes on the API filesystem under `UPLOAD_DIR`, served at `/uploads/...`.

## Railway volume (recommended)

Railway containers use **ephemeral disk** by default. Redeploys wipe uploaded files unless you attach a volume.

### Setup

1. Open the **API** service in Railway (root directory `backend/`).
2. Add a **Volume** and mount it at:

   ```
   /app/uploads
   ```

3. Set the API environment variable:

   ```
   UPLOAD_DIR=/app/uploads
   ```

4. Redeploy the API service.

5. Verify persistence:

   - Upload a test artwork photo.
   - Trigger a redeploy.
   - Confirm the image still loads.

6. Check admin health (admin login required):

   ```
   GET /api/admin/upload-health
   ```

   - `persistent: true` when `UPLOAD_DIR` resolves to `/app/uploads`
   - `missing_count` should be `0` for healthy storage
   - `records` lists database paths with no file on disk (common after a redeploy **before** the volume is attached)

### What gets stored

| Path under `UPLOAD_DIR` | Content |
|-------------------------|---------|
| `artworks/{id}/` | Normalized WebP variants (`_display`, `_master`, `_thumb`) |
| `labels/` | Museum label photos |
| `audio-notes/` | Voice note recordings |

### Fallback behavior

The API keeps `strip_missing_upload_files` enabled: if a `/uploads/...` path is in the database but the file is missing, responses omit the broken path and fall back to museum `catalog_*` URLs when available. The UI shows a placeholder instead of a broken image icon.

### Startup warning

In production (`APP_ENV=production`), the API logs a warning at startup when `UPLOAD_STORAGE_BACKEND=filesystem` and `UPLOAD_DIR` is **not** the persistent mount path `/app/uploads`.

## Future object storage (S3 / R2)

The codebase defines an `UploadStorage` adapter interface in `backend/app/services/upload_storage.py`:

- `filesystem` — current default
- `s3` — placeholder (not implemented)
- `r2` — placeholder (not implemented)

Set `UPLOAD_STORAGE_BACKEND=filesystem` until an object storage adapter is implemented. Object backends will be treated as persistent in production checks.

## Local development

Default `UPLOAD_DIR=uploads` (relative to the API working directory) is fine for local dev. Files live in `backend/uploads/` and survive restarts, but not Railway redeploys.
