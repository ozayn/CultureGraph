import logging

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import require_admin_user
from app.auth.google import GoogleAuthConfigurationError, GoogleAuthError, verify_google_id_token
from app.auth.jwt import AuthConfigurationError, create_access_token
from app.config import settings
from app.schemas import AuthTokenResponse, AuthUserRead, GoogleAuthRequest

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


@router.post("/google", response_model=AuthTokenResponse)
def google_login(payload: GoogleAuthRequest) -> AuthTokenResponse:
    logger.info("Google login request received")

    if not settings.jwt_secret or not settings.jwt_secret.strip():
        logger.warning("Google login rejected: JWT_SECRET missing")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT_SECRET is not configured on the server.",
        )

    if not settings.admin_email_set:
        logger.warning("Google login rejected: ADMIN_EMAILS missing")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_EMAILS is not configured on the server.",
        )

    try:
        profile = verify_google_id_token(payload.id_token)
    except GoogleAuthConfigurationError as exc:
        logger.warning("Google login rejected: Google auth misconfigured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except GoogleAuthError as exc:
        logger.info("Google token verified: no")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    logger.info("Google token verified: yes")

    admin_matched = profile.email in settings.admin_email_set
    logger.info("Admin email matched: %s", "yes" if admin_matched else "no")

    if not admin_matched:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This Google account is not authorized to edit CultureGraph.",
        )

    try:
        access_token = create_access_token(
            profile.email,
            name=profile.name,
            picture=profile.picture,
        )
    except AuthConfigurationError as exc:
        logger.warning("Google login rejected: JWT issue failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    logger.info("JWT issued: yes")

    return AuthTokenResponse(
        access_token=access_token,
        user=AuthUserRead(
            email=profile.email,
            name=profile.name,
            picture=profile.picture,
        ),
    )


@router.get("/me", response_model=AuthUserRead)
def auth_me(user: Annotated[dict[str, str | None], Depends(require_admin_user)]) -> AuthUserRead:
    return AuthUserRead(
        email=user["email"] or "",
        name=user.get("name"),
        picture=user.get("picture"),
    )
