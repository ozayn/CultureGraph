"""Upload storage backends and production persistence checks."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal, Protocol

from app.config import settings

logger = logging.getLogger(__name__)

UploadStorageBackend = Literal["filesystem", "s3", "r2"]

# Railway volume mount path documented in docs/UPLOAD_STORAGE.md
RAILWAY_PERSISTENT_UPLOAD_DIR = Path("/app/uploads")


class UploadStorage(Protocol):
    """Future-facing interface for local disk or object storage (S3/R2)."""

    @property
    def backend_name(self) -> UploadStorageBackend: ...

    def upload_root(self) -> Path: ...

    def is_persistent(self) -> bool: ...

    def public_url(self, relative_path: str) -> str: ...

    def write_bytes(self, relative_path: str, data: bytes) -> None: ...

    def exists(self, url_or_relative: str | None) -> bool: ...

    def delete(self, url_or_relative: str | None) -> None: ...


class FilesystemUploadStorage:
    backend_name: UploadStorageBackend = "filesystem"

    def __init__(self, upload_dir: str | Path) -> None:
        self._root = Path(upload_dir).resolve()

    def upload_root(self) -> Path:
        return self._root

    def is_persistent(self) -> bool:
        return is_persistent_upload_dir(self._root)

    def public_url(self, relative_path: str) -> str:
        cleaned = relative_path.lstrip("/")
        return f"/uploads/{cleaned}"

    def write_bytes(self, relative_path: str, data: bytes) -> None:
        target = self._safe_path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def exists(self, url_or_relative: str | None) -> bool:
        if not url_or_relative:
            return False
        target = self._safe_path(url_or_relative)
        return target.is_file()

    def delete(self, url_or_relative: str | None) -> None:
        if not url_or_relative:
            return
        target = self._safe_path(url_or_relative)
        if target.is_file():
            target.unlink()

    def _safe_path(self, url_or_relative: str) -> Path:
        from app.services.artwork_image_urls import upload_relative_path

        rel = upload_relative_path(url_or_relative)
        if not rel:
            rel = url_or_relative.lstrip("/")
        target = (self._root / rel).resolve()
        if self._root not in target.parents and target != self._root:
            raise ValueError("Upload path escapes upload root.")
        return target


class S3UploadStorage:
    """Placeholder for a future S3-compatible object storage adapter."""

    backend_name: UploadStorageBackend = "s3"

    def __init__(self) -> None:
        raise NotImplementedError(
            "S3 upload storage is not configured. Set UPLOAD_STORAGE_BACKEND=filesystem "
            "or implement S3UploadStorage with bucket credentials."
        )


class R2UploadStorage:
    """Placeholder for a future Cloudflare R2 adapter."""

    backend_name: UploadStorageBackend = "r2"

    def __init__(self) -> None:
        raise NotImplementedError(
            "R2 upload storage is not configured. Set UPLOAD_STORAGE_BACKEND=filesystem "
            "or implement R2UploadStorage with bucket credentials."
        )


def is_persistent_upload_dir(upload_dir: str | Path) -> bool:
    resolved = Path(upload_dir).resolve()
    if resolved == RAILWAY_PERSISTENT_UPLOAD_DIR.resolve():
        return True
    # Object storage backends are durable even though they are not local paths.
    backend = settings.upload_storage_backend.strip().lower()
    return backend in {"s3", "r2"}


def get_upload_storage() -> UploadStorage:
    backend = settings.upload_storage_backend.strip().lower()
    if backend == "filesystem":
        return FilesystemUploadStorage(settings.upload_dir)
    if backend == "s3":
        return S3UploadStorage()
    if backend == "r2":
        return R2UploadStorage()
    raise ValueError(f"Unsupported UPLOAD_STORAGE_BACKEND: {backend!r}")


def log_upload_storage_status() -> None:
    storage = get_upload_storage()
    root = storage.upload_root()
    root.mkdir(parents=True, exist_ok=True)
    persistent = storage.is_persistent()
    message = (
        f"Upload storage: backend={storage.backend_name} dir={root} "
        f"persistent={'yes' if persistent else 'no'}"
    )
    print(f"CultureGraph — {message}", flush=True)

    if settings.is_production and storage.backend_name == "filesystem" and not persistent:
        warning = (
            "WARNING: UPLOAD_DIR is not on a persistent Railway volume. "
            "Uploaded images and audio will be lost on redeploy. "
            "Mount a volume at /app/uploads and set UPLOAD_DIR=/app/uploads. "
            "See docs/UPLOAD_STORAGE.md."
        )
        print(f"CultureGraph — {warning}", flush=True)
        logger.warning(warning)
