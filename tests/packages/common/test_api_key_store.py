"""Tests for Redis API key store."""

import hashlib
from datetime import UTC, datetime

import pytest
import redis.asyncio as redis

from packages.common.api_key_store import ApiKeyStore
from packages.schemas.api_key import ApiKey


@pytest.fixture
async def redis_client() -> None:
    """Create Redis client for testing."""
    client = await redis.from_url("redis://localhost:4202", decode_responses=True)
    yield client
    await client.flushdb()  # Clean up
    await client.aclose()


@pytest.fixture
def api_key_store(redis_client) -> None:
    """Create ApiKeyStore instance."""
    return ApiKeyStore(redis_client)


@pytest.mark.asyncio
async def test_store_and_validate_api_key(api_key_store) -> None:
    """Test storing and validating API key."""
    # Create API key
    raw_key = "sk_test_abc123def456"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    api_key = ApiKey(
        key_id="key_test_1",
        key_hash=key_hash,
        name="Test Key",
        created_at=datetime.now(UTC),
        last_used_at=None,
        rate_limit_rpm=60,
        is_active=True,
    )

    # Store key
    await api_key_store.store(api_key)

    # Validate correct key
    is_valid = await api_key_store.validate(raw_key)
    assert is_valid is True

    # Validate incorrect key
    is_valid = await api_key_store.validate("sk_test_wrong")
    assert is_valid is False


@pytest.mark.asyncio
async def test_inactive_key_fails_validation(api_key_store) -> None:
    """Test that inactive keys fail validation."""
    raw_key = "sk_test_inactive"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    api_key = ApiKey(
        key_id="key_inactive",
        key_hash=key_hash,
        name="Inactive Key",
        created_at=datetime.now(UTC),
        last_used_at=None,
        rate_limit_rpm=60,
        is_active=False,  # Inactive
    )

    await api_key_store.store(api_key)

    is_valid = await api_key_store.validate(raw_key)
    assert is_valid is False
