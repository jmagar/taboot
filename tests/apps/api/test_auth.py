"""Tests for API authentication."""

from __future__ import annotations

import hashlib
import os
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
import redis.asyncio as redis
from fastapi import HTTPException
from fastapi.testclient import TestClient

from apps.api.deps.auth import verify_api_key
from packages.common.api_key_store import ApiKeyStore
from packages.schemas.api_key import ApiKey


@pytest.fixture(scope="module", autouse=True)
def set_test_env() -> Iterator[None]:
    """Set environment variables before TestClient is created."""
    # Ensure config can load without validation errors
    os.environ["RERANKER_BATCH_SIZE"] = "16"
    os.environ["OLLAMA_PORT"] = "11434"
    os.environ["FIRECRAWL_API_URL"] = "http://localhost:3002"
    os.environ["REDIS_URL"] = "redis://localhost:6379"
    os.environ["QDRANT_URL"] = "http://localhost:6333"
    os.environ["NEO4J_URI"] = "bolt://localhost:7687"
    os.environ["TEI_EMBEDDING_URL"] = "http://localhost:80"
    yield


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    from apps.api.app import app

    return TestClient(app)


@pytest.fixture
async def redis_client() -> AsyncIterator[redis.Redis[Any]]:
    """Create Redis client for testing."""
    client = await redis.from_url("redis://localhost:6379", decode_responses=True)
    yield client
    await client.flushdb()  # Clean up
    await client.close()


@pytest.mark.asyncio
async def test_verify_api_key_success(redis_client: redis.Redis[Any]) -> None:
    """Test successful API key verification."""
    # Store valid key
    raw_key = "sk_test_valid"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    api_key = ApiKey(
        key_id="key_valid",
        key_hash=key_hash,
        name="Valid Key",
        created_at=datetime.now(UTC),
        last_used_at=None,
        rate_limit_rpm=60,
        is_active=True,
    )

    store = ApiKeyStore(redis_client)
    await store.store(api_key)

    # Verify key
    result = await verify_api_key(raw_key, redis_client)
    assert result is True


@pytest.mark.asyncio
async def test_verify_api_key_invalid(redis_client: redis.Redis[Any]) -> None:
    """Test invalid API key raises 401."""
    with pytest.raises(HTTPException) as exc_info:
        await verify_api_key("sk_test_invalid", redis_client)

    assert exc_info.value.status_code == 401
    assert "Invalid API key" in exc_info.value.detail
