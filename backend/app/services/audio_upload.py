"""Store uploaded audio notes."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import settings
from app.services.image_upload import read_upload_with_limit

ACCEPTED_AUDIO_EXTENSIONS = {".webm", ".mp4", ".m4a", ".wav"}
ACCEPTED_AUDIO_MIME_TYPES = {
    "audio/webm",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "video/webm",
    "video/mp4",
}


def validate_audio_upload(filename: str | None, content_type: str | None) -> str:
    suffix = Path(filename or "").suffix.lower()
    if content_type and content_type.lower() not in ACCEPTED_AUDIO_MIME_TYPES:
        if suffix not in ACCEPTED_AUDIO_EXTENSIONS:
            raise HTTPException(
                status_code=415,
                detail="Unsupported audio type. Upload webm, mp4, m4a, or wav.",
            )

    if suffix and suffix not in ACCEPTED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail="Unsupported audio type. Upload webm, mp4, m4a, or wav.",
        )

    if suffix:
        return suffix
    if content_type and "webm" in content_type:
        return ".webm"
    if content_type and "wav" in content_type:
        return ".wav"
    return ".webm"


def validate_audio_duration(duration_seconds: float | None) -> float | None:
    if duration_seconds is None:
        return None
    if duration_seconds <= 0:
        raise HTTPException(status_code=400, detail="Recording duration must be positive.")
    if duration_seconds > settings.audio_note_max_duration_seconds:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Recording too long. Maximum length is "
                f"{int(settings.audio_note_max_duration_seconds // 60)} minutes."
            ),
        )
    return round(duration_seconds, 2)


async def read_audio_upload(file: UploadFile) -> bytes:
    return await read_upload_with_limit(file, settings.audio_note_max_bytes)


def save_audio_note_file(data: bytes, *, suffix: str) -> tuple[str, Path]:
    token = uuid.uuid4().hex[:12]
    upload_root = Path(settings.upload_dir).resolve()
    audio_dir = upload_root / "audio-notes"
    audio_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{token}{suffix}"
    path = audio_dir / filename
    path.write_bytes(data)
    return f"/uploads/audio-notes/{filename}", path


def remove_audio_note_file(audio_url: str | None) -> None:
    if not audio_url:
        return
    relative = audio_url.removeprefix("/uploads/").lstrip("/")
    path = (Path(settings.upload_dir).resolve() / relative).resolve()
    upload_root = Path(settings.upload_dir).resolve()
    if upload_root not in path.parents:
        return
    if path.is_file():
        path.unlink()
