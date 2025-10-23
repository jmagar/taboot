"""Authentication dependencies for FastAPI."""

import logging

import redis.asyncio as redis
from fastapi import Depends, Header, HTTPException, status

from packages.common.api_key_store import ApiKeyStore

logger = logging.getLogger(__name__)


async def get_redis_client() -> redis.Redis:
    """Get Redis client from app state.

    Returns:
        redis.Redis: Async Redis client.
    """
    from apps.api.app import app

    return app.state.redis


async def verify_api_key(
    x_api_key: str | None = Header(None, description="API key for authentication"),
    redis_client: redis.Redis = Depends(get_redis_client),
) -> bool:
    """Verify API key from X-API-Key header.

    Args:
        x_api_key: API key from header (optional).
        redis_client: Redis client for key validation.

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


__all__ = ["verify_api_key", "get_redis_client"]
