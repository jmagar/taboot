"""Authentication dependencies for FastAPI."""

from __future__ import annotations

import logging
from typing import Annotated, cast

from fastapi import Depends, Header, HTTPException, Request, status
from redis.asyncio import Redis

from packages.common.api_key_store import ApiKeyStore

logger = logging.getLogger(__name__)


async def get_redis_client(request: Request) -> Redis[bytes]:
    """Get Redis client from app state via Request.

    Args:
        request: FastAPI Request object (injected).

    Returns:
        redis.Redis[bytes]: Async Redis client (returns bytes, not decoded strings).
    """
    return cast(Redis[bytes], request.app.state.redis)


async def verify_api_key(
    redis_client: Annotated[Redis[bytes], Depends(get_redis_client)],  # noqa: B008
    x_api_key: Annotated[str | None, Header(description="API key for authentication")] = None,
) -> bool:
    """Verify API key from X-API-Key header.

    Args:
        redis_client: Redis client for key validation (injected via Depends).
        x_api_key: API key from header (optional).

    Returns:
        bool: True if key is valid.

    Raises:
        HTTPException: 401 if key is missing, invalid, or inactive.
    """
    if not x_api_key:
        logger.warning("Missing API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    store = ApiKeyStore(redis_client)

    is_valid = await store.validate(x_api_key)

    if not is_valid:
        logger.warning("Invalid API key attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    logger.debug("API key validated successfully")
    return True


__all__ = ["get_redis_client", "verify_api_key"]
