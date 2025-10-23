"""Shared pytest fixtures for Taboot test suite.

Provides common fixtures for mocking services, test configurations,
and test data factories used across all test modules.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import pytest

from packages.common.config import TabootConfig
from packages.schemas.models import (
    Document,
    SourceType,
    ExtractionState,
    Service,
    Host,
)
from tests.utils.mocks import (
    create_mock_neo4j_driver,
    create_mock_qdrant_client,
    create_mock_redis_client,
)


# ========== Configuration Fixtures ==========


@pytest.fixture
def test_config() -> TabootConfig:
    """Provide test configuration with in-memory/test service URLs.

    Returns:
        TabootConfig: Configuration instance for testing.
    """
    return TabootConfig(
        firecrawl_api_url="http://test-crawler:3002",
        redis_url="redis://test-cache:6379",
        qdrant_url="http://test-vectors:6333",
        neo4j_uri="bolt://test-graph:7687",
        tei_embedding_url="http://test-embed:80",
        reranker_url="http://test-rerank:8000",
        neo4j_user="test",
        neo4j_password="test",
        neo4j_db="test",
        log_level="DEBUG",
        reranker_batch_size=16,
        ollama_port=11434,
    )


# ========== Mock Service Fixtures ==========


@pytest.fixture
def mock_neo4j_driver(mocker: Any) -> Any:
    """Mock Neo4j driver for unit tests.

    Args:
        mocker: pytest-mock fixture.

    Returns:
        Mock Neo4j driver instance.
    """
    return create_mock_neo4j_driver(mocker)


@pytest.fixture
def mock_qdrant_client(mocker: Any) -> Any:
    """Mock Qdrant client for unit tests.

    Args:
        mocker: pytest-mock fixture.

    Returns:
        Mock Qdrant client instance.
    """
    return create_mock_qdrant_client(mocker)


@pytest.fixture
def mock_redis_client(mocker: Any) -> Any:
    """Mock Redis client for unit tests.

    Args:
        mocker: pytest-mock fixture.

    Returns:
        Mock Redis client instance.
    """
    return create_mock_redis_client(mocker)


# ========== Test Data Factories ==========


@pytest.fixture
def sample_document() -> Document:
    """Create a sample Document instance for testing.

    Returns:
        Document: A valid Document instance.
    """
    return Document(
        doc_id=uuid4(),
        source_url="https://example.com/docs/test",
        source_type=SourceType.WEB,
        content_hash="a" * 64,
        ingested_at=datetime.now(timezone.utc),
        extraction_state=ExtractionState.PENDING,
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_service() -> Service:
    """Create a sample Service instance for testing.

    Returns:
        Service: A valid Service instance.
    """
    now = datetime.now(timezone.utc)
    return Service(
        name="test-api-service",
        description="Test API service",
        image="test/api:latest",
        version="1.0.0",
        metadata={"env": "test"},
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def sample_host() -> Host:
    """Create a sample Host instance for testing.

    Returns:
        Host: A valid Host instance.
    """
    now = datetime.now(timezone.utc)
    return Host(
        hostname="test-server-01.example.com",
        ip_addresses=["192.168.1.10", "10.0.0.5"],
        os="Ubuntu 22.04",
        location="us-east-1a",
        created_at=now,
        updated_at=now,
    )


# ========== Factory Functions ==========


@pytest.fixture
def document_factory() -> Any:
    """Factory function for creating Document instances.

    Returns:
        Callable: Function that creates Document instances with custom parameters.

    Example:
        >>> doc = document_factory(source_type=SourceType.GITHUB)
    """
    def _create_document(**kwargs: Any) -> Document:
        """Create a Document with custom parameters.

        Args:
            **kwargs: Override default Document fields.

        Returns:
            Document: Document instance.
        """
        defaults = {
            "doc_id": uuid4(),
            "source_url": "https://example.com/docs/test",
            "source_type": SourceType.WEB,
            "content_hash": "a" * 64,
            "ingested_at": datetime.now(timezone.utc),
            "extraction_state": ExtractionState.PENDING,
            "updated_at": datetime.now(timezone.utc),
        }
        defaults.update(kwargs)
        return Document(**defaults)

    return _create_document


@pytest.fixture
def service_factory() -> Any:
    """Factory function for creating Service instances.

    Returns:
        Callable: Function that creates Service instances with custom parameters.

    Example:
        >>> svc = service_factory(name="custom-service", version="2.0.0")
    """
    def _create_service(**kwargs: Any) -> Service:
        """Create a Service with custom parameters.

        Args:
            **kwargs: Override default Service fields.

        Returns:
            Service: Service instance.
        """
        now = datetime.now(timezone.utc)
        defaults = {
            "name": f"test-service-{uuid4().hex[:8]}",
            "description": "Test service",
            "image": "test/service:latest",
            "version": "1.0.0",
            "created_at": now,
            "updated_at": now,
        }
        defaults.update(kwargs)
        return Service(**defaults)

    return _create_service


# ========== Docker Services Fixtures (for integration tests) ==========


@pytest.fixture(scope="session")
def docker_services_ready() -> None:
    """Wait for Docker services to be ready before running integration tests.

    This fixture checks if all required Docker services are healthy.
    Services must be started manually via `docker compose up -d` before running tests.

    Note:
        This fixture requires Docker Compose to be running with all services healthy.
        Tests marked with @pytest.mark.integration depend on this.

    Raises:
        pytest.skip: If any required service is not available.
    """
    # Import here to avoid dependency for unit tests
    import time
    import requests

    def is_responsive(url: str) -> bool:
        """Check if a service is responsive.

        Args:
            url: URL to check.

        Returns:
            bool: True if service responds successfully.
        """
        try:
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False

    # Check for required services
    # Use ports from .env.example that map to host
    services = [
        ("http://localhost:7000/", "Qdrant"),  # QDRANT_HTTP_PORT=7000
        ("http://localhost:7474/", "Neo4j"),  # NEO4J_HTTP_PORT=7474
        ("http://localhost:8080/health", "TEI"),  # TEI_HTTP_PORT=8080
        ("http://localhost:3002/", "Firecrawl"),  # FIRECRAWL_PORT=3002
    ]

    # Quick check first (no retry)
    unavailable = []
    for url, name in services:
        if not is_responsive(url):
            unavailable.append(name)

    # If any service is unavailable, skip the test
    if unavailable:
        pytest.skip(
            f"Docker services not ready: {', '.join(unavailable)}. "
            f"Start services with: docker compose up -d"
        )

    # All services available - log success
    print("\n✓ All Docker services ready for integration tests")


# ========== Pytest Configuration ==========


def pytest_configure(config: Any) -> None:
    """Configure pytest markers.

    Args:
        config: pytest config object.
    """
    config.addinivalue_line(
        "markers",
        "unit: Fast unit tests with mocked dependencies (no Docker required)",
    )
    config.addinivalue_line(
        "markers",
        "integration: Integration tests requiring Docker services to be healthy",
    )
    config.addinivalue_line(
        "markers",
        "slow: Long-running tests (>5 seconds)",
    )
