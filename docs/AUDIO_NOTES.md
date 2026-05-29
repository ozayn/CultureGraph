# Audio notes

Voice notes recorded in the gallery are stored as uploaded audio files with optional Whisper transcription and Claude interpretation.

## Storage on Railway

Audio files are written under `UPLOAD_DIR/audio-notes` (default: `uploads/audio-notes`).

**Railway’s default filesystem is ephemeral.** Without persistent storage, uploaded audio is lost on redeploy or when the container restarts.

For production:

1. Mount a **persistent volume** on the API service and set `UPLOAD_DIR` to that mount (same pattern as artwork images), **or**
2. Move audio to **object storage** (S3, R2, etc.) and store the public/signed URL on `AudioNote.audio_url`.

Until one of these is configured, treat audio notes as a development or single-instance convenience feature.

## Environment

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | Whisper transcription via OpenAI |
| `OPENAI_TRANSCRIPTION_MODEL` | Default `whisper-1` |
| `AUDIO_NOTE_MAX_BYTES` | Default 25MB |
| `ANTHROPIC_API_KEY` | Structured interpretation (falls back to transcript-only if unset) |

If `OPENAI_API_KEY` is missing, admins can type a transcript manually before interpretation.

## Limits

- Max duration: 5 minutes (client timer + `duration_seconds` validation)
- Max file size: 25MB (configurable)
- Accepted types: webm, mp4, m4a, wav

## API (admin only)

- `POST /api/audio-notes` — upload audio (`visit_id` and/or `artwork_id`)
- `GET /api/audio-notes?visit_id=&artwork_id=`
- `PATCH /api/audio-notes/{id}` — edit transcript / cleaned note
- `POST /api/audio-notes/{id}/transcribe` — Whisper or manual transcript in body
- `POST /api/audio-notes/{id}/interpret` — structured JSON interpretation
- `DELETE /api/audio-notes/{id}`

Public users cannot upload or transcribe audio notes in the current release.
