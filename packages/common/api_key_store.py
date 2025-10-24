"""Redis-backed API key store for authentication."""

import hashlib
import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from redis.asyncio import Redis

from packages.schemas.api_key import ApiKey

logger = logging.getLogger(__name__)


class ApiKeyStore:
    """Redis-backed API key store.

    Stores API key metadata indexed by key hash for O(1) validation.
    Key format: "api_key:{key_hash}" -> JSON serialized ApiKey
    """

    def __init__(self, redis_client: "Redis[bytes]") -> None:
        """Initialize with Redis client.

        Args:
            redis_client: Async Redis client.
        """
        self.redis = redis_client
        logger.info("Initialized ApiKeyStore")

    async def store(self, api_key: ApiKey) -> None:
        """Store API key metadata.

        Args:
            api_key: ApiKey model to persist.
        """
        key = f"api_key:{api_key.key_hash}"
        value = api_key.model_dump_json()

        await self.redis.set(key, value)
        logger.debug(f"Stored API key {api_key.key_id}")

    async def validate(self, raw_key: str) -> bool:
        """Validate API key.

        Args:
            raw_key: Raw API key string to validate.

        Returns:
            bool: True if key is valid and active, False otherwise.
        """
        # Hash the raw key
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        # Look up in Redis
        key = f"api_key:{key_hash}"
        value = await self.redis.get(key)

        if not value:
            logger.debug(f"API key not found: {key_hash[:8]}...")
            return False

        # Parse and check active status
        api_key_data = json.loads(value.decode("utf-8"))
        is_active = api_key_data.get("is_active", False)

        if not is_active:
            logger.debug(f"API key inactive: {key_hash[:8]}...")
            return False

        logger.debug(f"API key validated: {key_hash[:8]}...")
        return True

    async def get_by_hash(self, key_hash: str) -> ApiKey | None:
        """Get API key by hash.

        Args:
            key_hash: SHA-256 hash of the key.

        Returns:
            ApiKey if found, None otherwise.
        """
        key = f"api_key:{key_hash}"
        value = await self.redis.get(key)

        if not value:
            return None

        return ApiKey.model_validate_json(value.decode("utf-8"))


__all__ = ["ApiKeyStore"]
