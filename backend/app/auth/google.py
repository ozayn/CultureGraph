from dataclasses import dataclass

from google.auth.transport import requests
from google.oauth2 import id_token

from app.config import settings


class GoogleAuthConfigurationError(Exception):
    """Raised when Google auth is misconfigured."""


class GoogleAuthError(Exception):
    """Raised when a Google ID token cannot be verified."""


@dataclass(frozen=True)
class GoogleProfile:
    email: str
    name: str | None = None
    picture: str | None = None


def verify_google_id_token(token: str) -> GoogleProfile:
    if not settings.google_client_id or not settings.google_client_id.strip():
        raise GoogleAuthConfigurationError("GOOGLE_CLIENT_ID is not configured.")

    try:
        payload = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            settings.google_client_id.strip(),
        )
    except ValueError as exc:
        raise GoogleAuthError("Invalid Google ID token.") from exc

    email = payload.get("email")
    if not isinstance(email, str) or not email.strip():
        raise GoogleAuthError("Google account email is unavailable.")

    if not payload.get("email_verified", False):
        raise GoogleAuthError("Google account email is not verified.")

    name = payload.get("name")
    picture = payload.get("picture")

    return GoogleProfile(
        email=email.strip().lower(),
        name=name.strip() if isinstance(name, str) and name.strip() else None,
        picture=picture.strip() if isinstance(picture, str) and picture.strip() else None,
    )
