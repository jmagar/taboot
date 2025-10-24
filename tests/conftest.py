"""Shared pytest fixtures for Taboot test suite.

Provides common fixtures for mocking services, test configurations,
and test data factories used across all test modules.
"""

import os
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest

from packages.common.config import TabootConfig
from packages.schemas.models import (
    Document,
    ExtractionState,
    Host,
    Service,
    SourceType,
)
from tests.utils.mocks import (
    create_mock_neo4j_driver,
    create_mock_qdrant_client,
    create_mock_redis_client,
)

# ========== Test Environment Setup ==========


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Set up test environment variables before any tests run.

    This fixture ensures that get_config() can successfully load
    configuration in the test environment without validation errors.
    """
    # Load .env file first if present (for integration tests)
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    # Set integer env vars that were causing validation errors
    # Use direct assignment to override any shell/direnv interpolation syntax
    os.environ["RERANKER_BATCH_SIZE"] = "16"
    os.environ["OLLAMA_PORT"] = "11434"

    # Set other required env vars with sensible test defaults
    os.environ.setdefault("FIRECRAWL_API_URL", "http://localhost:3002")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
    os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
    os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
    os.environ.setdefault("NEO4J_USER", "neo4j")
    os.environ.setdefault("NEO4J_PASSWORD", "changeme")
    os.environ.setdefault("TEI_EMBEDDING_URL", "http://localhost:80")
    os.environ.setdefault("POSTGRES_USER", "taboot")
    os.environ.setdefault("POSTGRES_PASSWORD", "test")
    os.environ.setdefault("POSTGRES_DB", "taboot")
    os.environ.setdefault("POSTGRES_PORT", "5432")

    yield


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
        ingested_at=datetime.now(UTC),
        extraction_state=ExtractionState.PENDING,
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_service() -> Service:
    """Create a sample Service instance for testing.

    Returns:
        Service: A valid Service instance.
    """
    now = datetime.now(UTC)
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
    now = datetime.now(UTC)
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
            "ingested_at": datetime.now(UTC),
            "extraction_state": ExtractionState.PENDING,
            "updated_at": datetime.now(UTC),
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
        now = datetime.now(UTC)
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


@pytest.fixture
def postgres_conn():
    """Create PostgreSQL connection for testing.

    Returns:
        psycopg2.connection: PostgreSQL connection object.
    """
    from packages.common.db_schema import get_postgres_client

    conn = get_postgres_client()
    yield conn
    conn.close()


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
    import requests
    from neo4j import GraphDatabase

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

    def is_neo4j_ready() -> bool:
        """Check if Neo4j bolt connection is ready.

        Returns:
            bool: True if Neo4j accepts connections.
        """
        try:
            # Environment should already be loaded by setup_test_env fixture
            neo4j_password = os.getenv("NEO4J_PASSWORD", "changeme")
            driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", neo4j_password))
            driver.verify_connectivity()
            driver.close()
            return True
        except Exception as e:
            # Print error for debugging
            import sys

            print(f"\nNeo4j connection failed: {e}", file=sys.stderr)
            return False

    # Check for required services
    # Use ports from .env.example that map to host
    http_services = [
        ("http://localhost:7000/", "Qdrant"),  # QDRANT_HTTP_PORT=7000
        ("http://localhost:8080/health", "TEI"),  # TEI_HTTP_PORT=8080
        ("http://localhost:3002/", "Firecrawl"),  # FIRECRAWL_PORT=3002
    ]

    # Quick check first (no retry)
    unavailable = []

    # Check HTTP services
    for url, name in http_services:
        if not is_responsive(url):
            unavailable.append(name)

    # Check Neo4j bolt connection
    if not is_neo4j_ready():
        unavailable.append("Neo4j (bolt)")

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
