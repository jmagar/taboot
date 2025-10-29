"""Tests for health check utilities (T017).

Following TDD: Write tests first (RED), then implement to pass (GREEN).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from packages.common.config import TabootConfig
from packages.common.health import (
    check_firecrawl_health,
    check_neo4j_health,
    check_ollama_health,
    check_playwright_health,
    check_qdrant_health,
    check_redis_health,
    check_system_health,
    check_tei_health,
)


@pytest.fixture
def mock_config() -> TabootConfig:
    """Provide a test configuration."""
    return TabootConfig(
        neo4j_uri="bolt://localhost:4206",
        neo4j_user="neo4j",
        neo4j_password="test",
        qdrant_url="http://localhost:4203",
        redis_url="redis://localhost:4202",
        tei_embedding_url="http://localhost:4207",
        ollama_url="http://localhost:4214",
        ollama_port=4214,
        firecrawl_api_url="http://localhost:4200",
        playwright_microservice_url="http://localhost:4213/scrape",
        reranker_batch_size=16,
    )


@pytest.mark.unit
class TestNeo4jHealth:
    """Test Neo4j health check."""

    @pytest.mark.asyncio
    async def test_neo4j_healthy(self, mock_config: TabootConfig) -> None:
        """Test Neo4j health check when service is healthy."""
        mock_driver = MagicMock()
        mock_driver.verify_connectivity = MagicMock()

        with (
            patch("packages.common.health.get_config", return_value=mock_config),
            patch("packages.common.health.GraphDatabase.driver", return_value=mock_driver),
        ):
            result = await check_neo4j_health()
            assert result is True
            mock_driver.verify_connectivity.assert_called_once()
            mock_driver.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_neo4j_unhealthy(self, mock_config: TabootConfig) -> None:
        """Test Neo4j health check when service is unhealthy."""
        mock_driver = MagicMock()
        mock_driver.verify_connectivity.side_effect = Exception("Connection failed")

        with (
            patch("packages.common.health.get_config", return_value=mock_config),
            patch("packages.common.health.GraphDatabase.driver", return_value=mock_driver),
        ):
            result = await check_neo4j_health()
            assert result is False
            mock_driver.close.assert_called_once()


@pytest.mark.unit
class TestQdrantHealth:
    """Test Qdrant health check."""

    @pytest.mark.asyncio
    async def test_qdrant_healthy(self, mock_config: TabootConfig) -> None:
        """Test Qdrant health check when service is healthy."""
        mock_response = AsyncMock()
        mock_response.status_code = 200

        with (
            patch("packages.common.health.get_config", return_value=mock_config),
            patch("packages.common.health.httpx.AsyncClient.get", return_value=mock_response),
        ):
            result = await check_qdrant_health()
            assert result is True

    @pytest.mark.asyncio
    async def test_qdrant_unhealthy_status(self, mock_config: TabootConfig) -> None:
        """Test Qdrant health check when service returns non-200 status."""
        mock_response = AsyncMock()
        mock_response.status_code = 500

        with (
            patch("packages.common.health.get_config", return_value=mock_config),
            patch("packages.common.health.httpx.AsyncClient.get", return_value=mock_response),
        ):
            result = await check_qdrant_health()
            assert result is False

    @pytest.mark.asyncio
    async def test_qdrant_unhealthy_timeout(self, mock_config: TabootConfig) -> None:
        """Test Qdrant health check when service times out."""
        with (
            patch("packages.common.health.get_config", return_value=mock_config),
            patch("packages.common.health.httpx.AsyncClient.get", side_effect=TimeoutError()),
        ):
            result = await check_qdrant_health()
            assert result is False


@pytest.mark.unit
class TestRedisHealth:
    """Test Redis health check."""

    @pytest.mark.asyncio
    async def test_redis_healthy(self, mock_config: TabootConfig) -> None:
        """Test Redis health check when service is healthy."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)

        with (
            patch("packages.common.health.get_config", return_value=mock_config),
            patch("packages.common.health.redis.from_url", return_value=mock_redis),
        ):
            result = await check_redis_health()
            assert result is True
            mock_redis.ping.assert_called_once()
            mock_redis.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_unhealthy(self, mock_config: TabootConfig) -> None:
        """Test Redis health check when service is unhealthy."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(side_effect=Exception("Connection failed"))

        with (
            patch("packages.common.health.get_config", return_value=mock_config),
            patch("packages.common.health.redis.from_url", return_value=mock_redis),
        ):
            result = await check_redis_health()
            assert result is False
            mock_redis.aclose.assert_called_once()


@pytest.mark.unit
class TestTEIHealth:
    """Test TEI health check."""

    @pytest.mark.asyncio
    async def test_tei_healthy(self, mock_config: TabootConfig) -> None:
        """Test TEI health check when service is healthy."""
        mock_response = AsyncMock()
        mock_response.status_code = 200

        with (
            patch("packages.common.health.get_config", return_value=mock_config),
            patch("packages.common.health.httpx.AsyncClient.get", return_value=mock_response),
        ):
            result = await check_tei_health()
            assert result is True

    @pytest.mark.asyncio
    async def test_tei_unhealthy(self, mock_config: TabootConfig) -> None:
        """Test TEI health check when service is unhealthy."""
        with (
            patch("packages.common.health.get_config", return_value=mock_config),
            patch("packages.common.health.httpx.AsyncClient.get", side_effect=Exception("Failed")),
        ):
            result = await check_tei_health()
            assert result is False


@pytest.mark.unit
class TestOllamaHealth:
    """Test Ollama health check."""

    @pytest.mark.asyncio
    async def test_ollama_healthy(self, mock_config: TabootConfig) -> None:
        """Test Ollama health check when service is healthy."""
        mock_response = AsyncMock()
        mock_response.status_code = 200

        with (
            patch("packages.common.health.get_config", return_value=mock_config),
            patch("packages.common.health.httpx.AsyncClient.get", return_value=mock_response) as mock_get,
        ):
            result = await check_ollama_health()
            assert result is True
            # Verify it uses config.ollama_url instead of hardcoded container name
            mock_get.assert_called_once()
            called_url = mock_get.call_args[0][0]
            assert "localhost" in called_url, "Should use localhost from config, not container name"

    @pytest.mark.asyncio
    async def test_ollama_unhealthy(self, mock_config: TabootConfig) -> None:
        """Test Ollama health check when service is unhealthy."""
        with (
            patch("packages.common.health.get_config", return_value=mock_config),
            patch("packages.common.health.httpx.AsyncClient.get", side_effect=Exception("Failed")),
        ):
            result = await check_ollama_health()
            assert result is False


@pytest.mark.unit
class TestFirecrawlHealth:
    """Test Firecrawl health check."""

    @pytest.mark.asyncio
    async def test_firecrawl_healthy(self, mock_config: TabootConfig) -> None:
        """Test Firecrawl health check when service is healthy."""
        mock_response = AsyncMock()
        mock_response.status_code = 200

        with (
            patch("packages.common.health.get_config", return_value=mock_config),
            patch("packages.common.health.httpx.AsyncClient.get", return_value=mock_response),
        ):
            result = await check_firecrawl_health()
            assert result is True

    @pytest.mark.asyncio
    async def test_firecrawl_unhealthy(self, mock_config: TabootConfig) -> None:
        """Test Firecrawl health check when service is unhealthy."""
        with (
            patch("packages.common.health.get_config", return_value=mock_config),
            patch("packages.common.health.httpx.AsyncClient.get", side_effect=Exception("Failed")),
        ):
            result = await check_firecrawl_health()
            assert result is False


@pytest.mark.unit
class TestPlaywrightHealth:
    """Test Playwright health check."""

    @pytest.mark.asyncio
    async def test_playwright_healthy(self, mock_config: TabootConfig) -> None:
        """Test Playwright health check when service is healthy."""
        mock_response = AsyncMock()
        mock_response.status_code = 200

        with (
            patch("packages.common.health.get_config", return_value=mock_config),
            patch("packages.common.health.httpx.AsyncClient.get", return_value=mock_response),
        ):
            result = await check_playwright_health()
            assert result is True

    @pytest.mark.asyncio
    async def test_playwright_unhealthy(self, mock_config: TabootConfig) -> None:
        """Test Playwright health check when service is unhealthy."""
        with (
            patch("packages.common.health.get_config", return_value=mock_config),
            patch("packages.common.health.httpx.AsyncClient.get", side_effect=Exception("Failed")),
        ):
            result = await check_playwright_health()
            assert result is False


@pytest.mark.unit
class TestSystemHealth:
    """Test aggregate system health check."""

    @pytest.mark.asyncio
    async def test_system_all_healthy(self) -> None:
        """Test system health when all services are healthy."""
        with (
            patch("packages.common.health.check_neo4j_health", return_value=True),
            patch("packages.common.health.check_qdrant_health", return_value=True),
            patch("packages.common.health.check_redis_health", return_value=True),
            patch("packages.common.health.check_tei_health", return_value=True),
            patch("packages.common.health.check_ollama_health", return_value=True),
            patch("packages.common.health.check_firecrawl_health", return_value=True),
            patch("packages.common.health.check_playwright_health", return_value=True),
        ):
            result = await check_system_health()
            assert result["healthy"] is True
            assert all(result["services"].values())
            assert len(result["services"]) == 7

    @pytest.mark.asyncio
    async def test_system_partial_unhealthy(self) -> None:
        """Test system health when some services are unhealthy."""
        with (
            patch("packages.common.health.check_neo4j_health", return_value=True),
            patch("packages.common.health.check_qdrant_health", return_value=False),
            patch("packages.common.health.check_redis_health", return_value=True),
            patch("packages.common.health.check_tei_health", return_value=False),
            patch("packages.common.health.check_ollama_health", return_value=True),
            patch("packages.common.health.check_firecrawl_health", return_value=True),
            patch("packages.common.health.check_playwright_health", return_value=True),
        ):
            result = await check_system_health()
            assert result["healthy"] is False
            assert result["services"]["neo4j"] is True
            assert result["services"]["qdrant"] is False
            assert result["services"]["tei"] is False
            assert result["services"]["redis"] is True

    @pytest.mark.asyncio
    async def test_system_all_unhealthy(self) -> None:
        """Test system health when all services are unhealthy."""
        with (
            patch("packages.common.health.check_neo4j_health", return_value=False),
            patch("packages.common.health.check_qdrant_health", return_value=False),
            patch("packages.common.health.check_redis_health", return_value=False),
            patch("packages.common.health.check_tei_health", return_value=False),
            patch("packages.common.health.check_ollama_health", return_value=False),
            patch("packages.common.health.check_firecrawl_health", return_value=False),
            patch("packages.common.health.check_playwright_health", return_value=False),
        ):
            result = await check_system_health()
            assert result["healthy"] is False
            assert not any(result["services"].values())
