import io

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.config import settings
from app.main import app


def _png_bytes() -> bytes:
    image = Image.new("RGB", (400, 300), color=(120, 80, 40))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_admin_upload_health_lists_missing_files(
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    upload_root = tmp_path / "uploads"
    upload_root.mkdir()
    monkeypatch.setattr(settings, "upload_dir", str(upload_root))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "Missing file artwork"},
        )
        artwork_id = artwork_response.json()["id"]

        upload_response = await client.post(
            f"/api/artworks/{artwork_id}/image",
            headers=auth_headers,
            files={"file": ("photo.png", _png_bytes(), "image/png")},
        )
        assert upload_response.status_code == 200
        image_url = upload_response.json()["image_url"]
        assert image_url

        # Simulate ephemeral deploy disk loss while DB rows remain.
        for path in upload_root.rglob("*"):
            if path.is_file():
                path.unlink()

        health_response = await client.get("/api/admin/upload-health", headers=auth_headers)

        assert health_response.status_code == 200
        payload = health_response.json()
        assert payload["missing_count"] >= 1
        assert payload["missing_record_count"] >= 1
        assert payload["persistent"] is False
        assert any(item["record_id"] == artwork_id for item in payload["records"])

        clear_response = await client.post(
            "/api/admin/upload-health/clear-missing",
            headers=auth_headers,
        )
        assert clear_response.status_code == 200
        assert clear_response.json()["cleared_paths"] >= 1
        assert clear_response.json()["affected_records"] >= 1

        health_after = await client.get("/api/admin/upload-health", headers=auth_headers)
        assert health_after.json()["missing_count"] == 0

        artwork_after = await client.get(f"/api/artworks/{artwork_id}", headers=auth_headers)
        assert artwork_after.json()["image_url"] is None


@pytest.mark.asyncio
async def test_admin_upload_health_requires_admin(auth_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unauth = await client.get("/api/admin/upload-health")
        assert unauth.status_code == 401

        from app.auth.jwt import create_access_token

        stranger = {"Authorization": f"Bearer {create_access_token('stranger@example.com')}"}
        forbidden = await client.get("/api/admin/upload-health", headers=stranger)
        assert forbidden.status_code == 403

        ok = await client.get("/api/admin/upload-health", headers=auth_headers)
        assert ok.status_code == 200

        clear_unauth = await client.post("/api/admin/upload-health/clear-missing")
        assert clear_unauth.status_code == 401

        clear_forbidden = await client.post(
            "/api/admin/upload-health/clear-missing",
            headers=stranger,
        )
        assert clear_forbidden.status_code == 403
