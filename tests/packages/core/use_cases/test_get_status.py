"""Tests for GetStatusUseCase - System status aggregation.

Tests the status aggregation use-case that collects:
- Service health status
- Queue depths (ingestion, extraction)
- System metrics snapshot

Following TDD pattern per T129-T130.
"""

from unittest.mock import AsyncMock

import pytest

from packages.common.health import SystemHealthStatus
from packages.core.use_cases.get_status import (
    GetStatusUseCase,
    MetricsSnapshot,
    QueueDepth,
    ServiceHealth,
    SystemStatus,
)


@pytest.fixture
def mock_redis() -> AsyncMock:
    """Mock Redis client for queue depth queries."""
    redis_mock = AsyncMock()
    # Default: empty queues
    redis_mock.llen = AsyncMock(return_value=0)
    return redis_mock


@pytest.fixture
def mock_health_checker() -> AsyncMock:
    """Mock health checker function."""
    health_mock = AsyncMock()
    # Default: all services healthy
    health_mock.return_value = SystemHealthStatus(
        healthy=True,
        services={
            "neo4j": True,
            "qdrant": True,
            "redis": True,
            "tei": True,
            "ollama": True,
            "firecrawl": True,
            "playwright": True,
        },
    )
    return health_mock


@pytest.fixture
def use_case(mock_redis: AsyncMock, mock_health_checker: AsyncMock) -> GetStatusUseCase:
    """Create GetStatusUseCase instance with mocked dependencies."""
    return GetStatusUseCase(
        redis_client=mock_redis,
        health_checker=mock_health_checker,
    )


@pytest.mark.asyncio
async def test_execute_returns_system_status_all_healthy(
    use_case: GetStatusUseCase,
    mock_redis: AsyncMock,
    mock_health_checker: AsyncMock,
) -> None:
    """Test execute returns SystemStatus with all services healthy."""
    # Arrange
    mock_redis.llen.side_effect = [0, 0]  # ingestion queue, extraction queue

    # Act
    status = await use_case.execute()

    # Assert
    assert isinstance(status, SystemStatus)
    assert status.overall_healthy is True
    assert len(status.services) == 7
    assert all(svc.healthy for svc in status.services.values())
    assert status.queue_depth.ingestion == 0
    assert status.queue_depth.extraction == 0
    assert status.metrics is not None


@pytest.mark.asyncio
async def test_execute_with_unhealthy_services(
    mock_redis: AsyncMock,
    mock_health_checker: AsyncMock,
) -> None:
    """Test execute returns partial failures when services are unhealthy."""
    # Arrange
    mock_health_checker.return_value = SystemHealthStatus(
        healthy=False,
        services={
            "neo4j": True,
            "qdrant": True,
            "redis": True,
            "tei": False,  # TEI is down
            "ollama": False,  # Ollama is down
            "firecrawl": True,
            "playwright": True,
        },
    )
    mock_redis.llen.side_effect = [5, 12]  # queues have items

    use_case = GetStatusUseCase(
        redis_client=mock_redis,
        health_checker=mock_health_checker,
    )

    # Act
    status = await use_case.execute()

    # Assert
    assert status.overall_healthy is False
    assert status.services["tei"].healthy is False
    assert status.services["ollama"].healthy is False
    assert status.services["neo4j"].healthy is True
    assert status.queue_depth.ingestion == 5
    assert status.queue_depth.extraction == 12


@pytest.mark.asyncio
async def test_execute_with_queue_depth(
    use_case: GetStatusUseCase,
    mock_redis: AsyncMock,
) -> None:
    """Test execute correctly queries Redis for queue depths."""
    # Arrange
    mock_redis.llen.side_effect = [42, 17]

    # Act
    status = await use_case.execute()

    # Assert
    assert status.queue_depth.ingestion == 42
    assert status.queue_depth.extraction == 17
    # Verify Redis was called with correct queue names
    assert mock_redis.llen.call_count == 2
    calls = [call.args[0] for call in mock_redis.llen.call_args_list]
    assert "queue:ingestion" in calls
    assert "queue:extraction" in calls


@pytest.mark.asyncio
async def test_execute_partial_failure_redis_unavailable(
    mock_health_checker: AsyncMock,
) -> None:
    """Test execute handles Redis failures gracefully (partial data)."""
    # Arrange
    mock_redis = AsyncMock()
    mock_redis.llen.side_effect = Exception("Redis connection failed")

    use_case = GetStatusUseCase(
        redis_client=mock_redis,
        health_checker=mock_health_checker,
    )

    # Act
    status = await use_case.execute()

    # Assert - returns what's available (health checks passed, queues unknown)
    assert isinstance(status, SystemStatus)
    assert status.overall_healthy is True  # health checks still passed
    assert status.queue_depth.ingestion == 0  # fallback to 0 on error
    assert status.queue_depth.extraction == 0


@pytest.mark.asyncio
async def test_execute_partial_failure_health_check_error(
    mock_redis: AsyncMock,
) -> None:
    """Test execute handles health check failures gracefully."""
    # Arrange
    mock_health_checker = AsyncMock()
    mock_health_checker.side_effect = Exception("Health check timeout")

    use_case = GetStatusUseCase(
        redis_client=mock_redis,
        health_checker=mock_health_checker,
    )

    # Act
    status = await use_case.execute()

    # Assert - returns what's available (all services marked unhealthy)
    assert isinstance(status, SystemStatus)
    assert status.overall_healthy is False
    assert all(not svc.healthy for svc in status.services.values())
    assert status.queue_depth.ingestion == 0
    assert status.queue_depth.extraction == 0


@pytest.mark.asyncio
async def test_service_health_model() -> None:
    """Test ServiceHealth model validation."""
    # Arrange & Act
    service = ServiceHealth(
        name="neo4j",
        healthy=True,
        message="Connected",
    )

    # Assert
    assert service.name == "neo4j"
    assert service.healthy is True
    assert service.message == "Connected"


@pytest.mark.asyncio
async def test_queue_depth_model() -> None:
    """Test QueueDepth model validation."""
    # Arrange & Act
    queue_depth = QueueDepth(
        ingestion=42,
        extraction=17,
    )

    # Assert
    assert queue_depth.ingestion == 42
    assert queue_depth.extraction == 17


@pytest.mark.asyncio
async def test_metrics_snapshot_model() -> None:
    """Test MetricsSnapshot model validation."""
    # Arrange & Act
    metrics = MetricsSnapshot(
        documents_ingested=1000,
        chunks_indexed=5000,
        extraction_jobs_completed=800,
        graph_nodes_created=2500,
    )

    # Assert
    assert metrics.documents_ingested == 1000
    assert metrics.chunks_indexed == 5000
    assert metrics.extraction_jobs_completed == 800
    assert metrics.graph_nodes_created == 2500


@pytest.mark.asyncio
async def test_system_status_model() -> None:
    """Test SystemStatus model validation."""
    # Arrange & Act
    status = SystemStatus(
        overall_healthy=True,
        services={
            "neo4j": ServiceHealth(name="neo4j", healthy=True),
            "qdrant": ServiceHealth(name="qdrant", healthy=True),
        },
        queue_depth=QueueDepth(ingestion=10, extraction=5),
        metrics=MetricsSnapshot(
            documents_ingested=100,
            chunks_indexed=500,
            extraction_jobs_completed=80,
            graph_nodes_created=250,
        ),
    )

    # Assert
    assert status.overall_healthy is True
    assert len(status.services) == 2
    assert status.queue_depth.ingestion == 10
    assert status.metrics.documents_ingested == 100
