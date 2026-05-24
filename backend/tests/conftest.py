import pytest

from app.auth.jwt import create_access_token
from app.config import settings


@pytest.fixture(autouse=True)
def configure_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "jwt_secret", "test-jwt-secret")
    monkeypatch.setattr(settings, "google_client_id", "test-google-client-id")
    monkeypatch.setattr(settings, "admin_emails", "admin@example.com,editor@example.com")


@pytest.fixture
def auth_headers() -> dict[str, str]:
    token = create_access_token("admin@example.com")
    return {"Authorization": f"Bearer {token}"}
