"""Fixtures for API tests."""

from __future__ import annotations

import hashlib
import os
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
import redis.asyncio as redis
from fastapi.testclient import TestClient

from packages.common.api_key_store import ApiKeyStore
from packages.schemas.api_key import ApiKey


@pytest.fixture(scope="session", autouse=True)
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


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    """Create FastAPI TestClient for API tests.

    Creates a test client after environment variables are set.
    This ensures get_config() can load successfully during app startup.
    """
    from apps.api.app import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def redis_client() -> AsyncIterator[redis.Redis[Any]]:
    """Create Redis client for testing."""
    client = await redis.from_url("redis://localhost:6379", decode_responses=True)
    yield client
    await client.flushdb()  # Clean up
    await client.close()


@pytest.fixture
async def valid_api_key(redis_client: redis.Redis[Any]) -> str:
    """Create and store valid API key."""
    raw_key = "sk_test_integration"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    api_key = ApiKey(
        key_id="key_integration",
        key_hash=key_hash,
        name="Integration Test Key",
        created_at=datetime.now(UTC),
        last_used_at=None,
        rate_limit_rpm=60,
        is_active=True,
    )

    store = ApiKeyStore(redis_client)
    await store.store(api_key)

    return raw_key
