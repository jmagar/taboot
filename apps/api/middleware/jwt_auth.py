"""JWT authentication middleware for Taboot API.

Validates JWT tokens from Better Auth (Next.js frontend) and extracts user information.
Tokens are passed via Authorization header: "Bearer <token>".

The middleware:
- Validates JWT signature using AUTH_SECRET
- Extracts user_id and session information from token payload
- Stores user context in request.state for use in route handlers
- Returns 401 Unauthorized for invalid/missing tokens (when required)

Usage in routes:
    from apps.api.middleware.jwt_auth import require_auth

    @router.get("/protected")
    async def protected_route(user_id: str = Depends(require_auth)):
        return {"user_id": user_id}
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Final, NotRequired, TypedDict, cast

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.requests import Request

from packages.common.config import ensure_env_loaded

logger = logging.getLogger(__name__)

ensure_env_loaded()


class AuthClaims(TypedDict, total=False):
    """Typed representation of Better Auth JWT claims."""

    sub: str
    userId: str
    sessionId: NotRequired[str]
    exp: int
    iat: NotRequired[int]
    nbf: NotRequired[int]
    iss: NotRequired[str]
    aud: NotRequired[str | list[str]]


AUTH_SECRET_ENV_VAR = "AUTH_SECRET"
JWT_ALGORITHM: Final[str] = "HS256"
MIN_SECRET_LENGTH: Final[int] = 32  # 256 bits for HS256

# HTTP Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def _get_auth_secret() -> str:
    """Get and validate the JWT signing secret from environment.

    Tries AUTH_SECRET first, falls back to BETTER_AUTH_SECRET if not set.
    This allows single-user systems to use one secret for both auth systems.

    Validates that secret meets minimum security requirements:
    - Minimum 32 characters (256 bits for HS256)
    - Basic entropy check (not all repeated characters)

    Returns:
        Validated auth secret value.

    Raises:
        RuntimeError: If no secret found, too short, or has insufficient entropy.
    """
    auth_secret = os.getenv(AUTH_SECRET_ENV_VAR) or os.getenv("BETTER_AUTH_SECRET")

    if not auth_secret:
        logger.error("AUTH_SECRET or BETTER_AUTH_SECRET required for JWT authentication")
        logger.info(
            "Generate AUTH_SECRET with: "
            "python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )
        raise RuntimeError("AUTH_SECRET environment variable required")

    # Validate minimum length (256 bits for HS256)
    if len(auth_secret) < MIN_SECRET_LENGTH:
        logger.error(
            "AUTH_SECRET too short",
            extra={"length": len(auth_secret), "minimum": MIN_SECRET_LENGTH},
        )
        logger.info(
            "Generate strong secret with: "
            "python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )
        raise RuntimeError(f"AUTH_SECRET too short: {len(auth_secret)} < {MIN_SECRET_LENGTH}")

    # Basic entropy check (not repeated characters)
    if len(set(auth_secret)) < MIN_SECRET_LENGTH // 2:
        logger.error("AUTH_SECRET has low entropy")
        logger.info(
            "Generate cryptographically random secret with: "
            "python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )
        raise RuntimeError("AUTH_SECRET has insufficient entropy")

    logger.debug("AUTH_SECRET validated", extra={"length": len(auth_secret)})
    return auth_secret


def _token_log_metadata(token: str, exc: Exception) -> dict[str, object | None]:
    """Collect non-PII metadata for structured logging."""
    extra: dict[str, object | None] = {"error": str(exc)}

    try:
        header: dict[str, object] = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError:
        header = {}

    kid = header.get("kid")
    if isinstance(kid, str):
        extra["kid"] = kid

    try:
        claims: dict[str, object] = jwt.decode(
            token,
            options={"verify_signature": False, "verify_aud": False},
            algorithms=[JWT_ALGORITHM],
        )
    except jwt.InvalidTokenError:
        return extra

    iss = claims.get("iss")
    if isinstance(iss, str):
        extra["iss"] = iss

    aud = claims.get("aud")
    if isinstance(aud, str | list):
        extra["aud"] = aud

    return extra


def decode_jwt(token: str) -> AuthClaims:
    """Decode and validate JWT token from Better Auth.

    Args:
        token: JWT token string from Authorization header.

    Returns:
        Decoded token payload containing user and session information.

    Raises:
        HTTPException: If token is invalid or expired.
    """
    try:
        payload_raw: dict[str, object] = jwt.decode(
            token,
            _get_auth_secret(),
            algorithms=[JWT_ALGORITHM],
            options={"verify_exp": True, "verify_signature": True, "require": ["exp"]},
        )
    except jwt.ExpiredSignatureError as exc:
        logger.warning("JWT token expired", extra=_token_log_metadata(token, exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidTokenError as exc:
        logger.warning("Invalid JWT token", extra=_token_log_metadata(token, exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    else:
        return cast(AuthClaims, payload_raw)


def get_current_user_optional(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),  # noqa: B008
) -> str | None:
    """Extract user_id from JWT token if present (optional authentication).

    Args:
        request: FastAPI request object.
        credentials: HTTP Bearer credentials from Authorization header.

    Returns:
        User ID from token payload, or None if no valid token provided.
    """
    if not credentials:
        return None

    try:
        payload = decode_jwt(credentials.credentials)
    except HTTPException:
        return None  # optional auth
    else:
        user_id = payload.get("sub") or payload.get("userId")
        if not isinstance(user_id, str):
            request_id = getattr(request.state, "request_id", None) or request.headers.get(
                "X-Request-ID"
            )
            logger.warning(
                "JWT token missing user identifier",
                extra={"request_id": request_id},
            )
            return None

        request.state.user_id = user_id
        session_id = payload.get("sessionId")
        if isinstance(session_id, str):
            request.state.session_id = session_id

        return user_id


def require_auth(
    user_id: str | None = Depends(get_current_user_optional),
) -> str:
    """Require valid JWT authentication (returns user_id or raises 401).

    Use this dependency in routes that require authentication:

        @router.get("/protected")
        async def protected_route(user_id: str = Depends(require_auth)):
            return {"user_id": user_id}

    Args:
        user_id: User ID from optional authentication dependency.

    Returns:
        User ID from authenticated token.

    Raises:
        HTTPException: 401 Unauthorized if no valid token provided.
    """
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id
