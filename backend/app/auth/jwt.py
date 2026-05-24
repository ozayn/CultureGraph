from datetime import UTC, datetime, timedelta

import jwt
from jwt import InvalidTokenError

from app.config import settings


class AuthConfigurationError(Exception):
    """Raised when JWT auth is misconfigured."""


def create_access_token(
    email: str,
    *,
    name: str | None = None,
    picture: str | None = None,
) -> str:
    if not settings.jwt_secret or not settings.jwt_secret.strip():
        raise AuthConfigurationError("JWT_SECRET is not configured.")

    now = datetime.now(UTC)
    payload: dict[str, str | datetime] = {
        "sub": email,
        "email": email,
        "iat": now,
        "exp": now + timedelta(days=settings.jwt_expiration_days),
    }
    if name:
        payload["name"] = name
    if picture:
        payload["picture"] = picture
    return jwt.encode(payload, settings.jwt_secret.strip(), algorithm="HS256")


def decode_access_token(token: str) -> dict[str, str | None]:
    if not settings.jwt_secret or not settings.jwt_secret.strip():
        raise AuthConfigurationError("JWT_SECRET is not configured.")

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.strip(),
            algorithms=["HS256"],
        )
    except InvalidTokenError as exc:
        raise InvalidTokenError("Invalid or expired token.") from exc

    email = payload.get("email") or payload.get("sub")
    if not isinstance(email, str) or not email.strip():
        raise InvalidTokenError("Token payload missing email.")

    name = payload.get("name")
    picture = payload.get("picture")

    return {
        "email": email.strip(),
        "name": name if isinstance(name, str) and name.strip() else None,
        "picture": picture if isinstance(picture, str) and picture.strip() else None,
    }
