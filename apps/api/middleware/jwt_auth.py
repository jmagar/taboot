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

import logging
import os
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.requests import Request

logger = logging.getLogger(__name__)

# Better Auth JWT configuration
AUTH_SECRET = os.getenv("AUTH_SECRET")
if not AUTH_SECRET:
    raise ValueError("AUTH_SECRET environment variable is required for JWT authentication")

# JWT algorithm used by Better Auth
JWT_ALGORITHM = "HS256"

# HTTP Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)


def decode_jwt(token: str) -> dict[str, Any]:
    """Decode and validate JWT token from Better Auth.

    Args:
        token: JWT token string from Authorization header.

    Returns:
        Decoded token payload containing user and session information.

    Raises:
        HTTPException: If token is invalid or expired.
    """
    try:
        # AUTH_SECRET is guaranteed to be a string (checked at module load)
        payload: dict[str, Any] = jwt.decode(
            token,
            AUTH_SECRET,  # type: ignore[arg-type]
            algorithms=[JWT_ALGORITHM],
            options={"verify_exp": True, "verify_signature": True},
        )
        return payload
    except jwt.ExpiredSignatureError as exc:
        logger.warning("JWT token expired", extra={"error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidTokenError as exc:
        logger.warning("Invalid JWT token", extra={"error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


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
        user_id: str | None = payload.get("sub") or payload.get("userId")

        if not user_id:
            logger.warning("JWT token missing user identifier")
            return None

        # Store user info in request state for access in handlers
        request.state.user_id = user_id
        request.state.session_id = payload.get("sessionId")

        return user_id

    except HTTPException:
        # Invalid token, but optional auth allows None
        return None


def require_auth(
    user_id: str | None = Depends(get_current_user_optional),  # noqa: B008
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
