"""Tests for Tier C LLM client."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from packages.extraction.tier_c.llm_client import TierCLLMClient
from packages.extraction.tier_c.schema import ExtractionResult, Triple


@pytest.fixture
def mock_ollama():
    """Mock Ollama client."""
    with patch("packages.extraction.tier_c.llm_client.ollama") as mock:
        mock.chat = AsyncMock(return_value={
            "message": {
                "content": '{"triples": [{"subject": "api", "predicate": "DEPENDS_ON", "object": "db", "confidence": 0.9}]}'
            }
        })
        yield mock


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock = Mock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock()
    return mock


class TestTierCLLMClient:
    """Test Ollama LLM client with batching and caching."""

    @pytest.mark.asyncio
    async def test_extract_from_window(self, mock_ollama, mock_redis):
        """Test extracting triples from a window."""
        client = TierCLLMClient(redis_client=mock_redis)

        window = "The api-service depends on postgres database."
        result = await client.extract_from_window(window)

        assert isinstance(result, ExtractionResult)
        assert len(result.triples) >= 1

    @pytest.mark.asyncio
    async def test_batch_extract(self, mock_ollama, mock_redis):
        """Test batch extraction."""
        client = TierCLLMClient(redis_client=mock_redis, batch_size=2)

        windows = [
            "api depends on db",
            "nginx routes to api",
            "redis caches data",
        ]

        results = await client.batch_extract(windows)

        assert len(results) == 3
        assert all(isinstance(r, ExtractionResult) for r in results)

    @pytest.mark.asyncio
    async def test_cache_hit(self, mock_ollama, mock_redis):
        """Test Redis cache hit."""
        cached_result = '{"triples": [{"subject": "cached", "predicate": "TEST", "object": "value", "confidence": 1.0}]}'
        mock_redis.get = AsyncMock(return_value=cached_result.encode())

        client = TierCLLMClient(redis_client=mock_redis)
        window = "test window"

        result = await client.extract_from_window(window)

        # Should use cached result
        assert result.triples[0].subject == "cached"
        # Should not call Ollama
        mock_ollama.chat.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss(self, mock_ollama, mock_redis):
        """Test Redis cache miss."""
        mock_redis.get = AsyncMock(return_value=None)

        client = TierCLLMClient(redis_client=mock_redis)
        window = "test window"

        result = await client.extract_from_window(window)

        # Should call Ollama
        mock_ollama.chat.assert_called_once()
        # Should cache result
        mock_redis.set.assert_called_once()
