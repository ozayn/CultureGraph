import pytest

from app.config import settings
from app.services.upload_storage import (
    FilesystemUploadStorage,
    RAILWAY_PERSISTENT_UPLOAD_DIR,
    is_persistent_upload_dir,
    log_upload_storage_status,
)


def test_railway_upload_dir_is_persistent() -> None:
    assert is_persistent_upload_dir(RAILWAY_PERSISTENT_UPLOAD_DIR) is True
    assert is_persistent_upload_dir("/app/uploads") is True


def test_default_local_upload_dir_is_not_persistent(tmp_path) -> None:
    local_dir = tmp_path / "uploads"
    local_dir.mkdir()
    assert is_persistent_upload_dir(local_dir) is False


def test_s3_backend_counts_as_persistent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "upload_storage_backend", "s3")
    assert is_persistent_upload_dir("uploads") is True


def test_filesystem_storage_public_url() -> None:
    storage = FilesystemUploadStorage("/tmp/uploads")
    assert storage.public_url("artworks/1/display.webp") == "/uploads/artworks/1/display.webp"


def test_startup_warns_when_production_uses_ephemeral_dir(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path,
) -> None:
    upload_dir = tmp_path / "ephemeral"
    upload_dir.mkdir()
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "upload_dir", str(upload_dir))
    monkeypatch.setattr(settings, "upload_storage_backend", "filesystem")

    log_upload_storage_status()
    captured = capsys.readouterr().out
    assert "persistent=no" in captured
    assert "WARNING: UPLOAD_DIR is not on a persistent Railway volume" in captured
