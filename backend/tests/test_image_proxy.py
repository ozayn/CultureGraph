from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_image_proxy_rejects_non_https() -> None:
    response = client.get("/api/image-proxy", params={"url": "http://ids.si.edu/x.jpg"})
    assert response.status_code == 400


def test_image_proxy_rejects_unknown_host() -> None:
    response = client.get("/api/image-proxy", params={"url": "https://evil.example/x.jpg"})
    assert response.status_code == 403


@patch("app.routers.media.requests.get")
def test_image_proxy_returns_upstream_image(mock_get: MagicMock) -> None:
    mock_get.return_value = MagicMock(
        status_code=200,
        content=b"fake-image",
        headers={"content-type": "image/jpeg"},
    )

    url = "https://ids.si.edu/ids/download?id=SAAM-1_thumb"
    response = client.get("/api/image-proxy", params={"url": url})

    assert response.status_code == 200
    assert response.content == b"fake-image"
    assert response.headers["content-type"] == "image/jpeg"
    mock_get.assert_called_once()
