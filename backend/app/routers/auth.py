from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import require_admin_user
from app.auth.google import GoogleAuthConfigurationError, GoogleAuthError, verify_google_id_token
from app.auth.jwt import AuthConfigurationError, create_access_token
from app.config import settings
from app.schemas import AuthTokenResponse, AuthUserRead, GoogleAuthRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/google", response_model=AuthTokenResponse)
def google_login(payload: GoogleAuthRequest) -> AuthTokenResponse:
    if not settings.jwt_secret or not settings.jwt_secret.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT_SECRET is not configured on the server.",
        )

    if not settings.admin_email_set:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_EMAILS is not configured on the server.",
        )

    try:
        email = verify_google_id_token(payload.id_token)
    except GoogleAuthConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except GoogleAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    if email not in settings.admin_email_set:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This Google account is not authorized to edit CultureGraph.",
        )

    try:
        access_token = create_access_token(email)
    except AuthConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return AuthTokenResponse(
        access_token=access_token,
        user=AuthUserRead(email=email),
    )


@router.get("/me", response_model=AuthUserRead)
def auth_me(user: Annotated[dict[str, str], Depends(require_admin_user)]) -> AuthUserRead:
    return AuthUserRead(email=user["email"])
