"""Tests for GET /status endpoint.

Tests T135-T136: System status API endpoint.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from apps.api.app import app
from packages.core.use_cases.get_status import (
    MetricsSnapshot,
    QueueDepth,
    ServiceHealth,
    SystemStatus,
)


@pytest.fixture
def client() -> TestClient:
    """Create test client for FastAPI app.

    Returns:
        TestClient: Test client instance.
    """
    return TestClient(app)


@pytest.fixture
def mock_system_status() -> SystemStatus:
    """Create mock SystemStatus for testing.

    Returns:
        SystemStatus: Mock status instance.
    """
    return SystemStatus(
        overall_healthy=True,
        services={
            "neo4j": ServiceHealth(name="neo4j", healthy=True, message=None),
            "qdrant": ServiceHealth(name="qdrant", healthy=True, message=None),
            "redis": ServiceHealth(name="redis", healthy=True, message=None),
            "tei": ServiceHealth(name="tei", healthy=True, message=None),
            "ollama": ServiceHealth(name="ollama", healthy=True, message=None),
            "firecrawl": ServiceHealth(name="firecrawl", healthy=True, message=None),
            "playwright": ServiceHealth(name="playwright", healthy=True, message=None),
        },
        queue_depth=QueueDepth(ingestion=0, extraction=0),
        metrics=MetricsSnapshot(
            documents_ingested=0,
            chunks_indexed=0,
            extraction_jobs_completed=0,
            graph_nodes_created=0,
        ),
    )


def test_status_returns_200(client: TestClient, mock_system_status: SystemStatus) -> None:
    """Test GET /status returns 200 OK.

    Verifies:
    - Status code is 200
    - Response has JSON body
    """
    with patch("apps.api.routes.status.get_status_use_case") as mock_get_use_case:
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = mock_system_status
        mock_get_use_case.return_value = mock_use_case

        response = client.get("/status")
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "application/json"


def test_status_has_required_fields(client: TestClient, mock_system_status: SystemStatus) -> None:
    """Test GET /status response has required fields.

    Verifies response contains:
    - overall_healthy (bool)
    - services (dict)
    - queue_depth (object with ingestion/extraction)
    - metrics (object)
    """
    with patch("apps.api.routes.status.get_status_use_case") as mock_get_use_case:
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = mock_system_status
        mock_get_use_case.return_value = mock_use_case

        response = client.get("/status")
        data = response.json()

        # Check top-level fields
        assert "overall_healthy" in data
        assert isinstance(data["overall_healthy"], bool)

        assert "services" in data
        assert isinstance(data["services"], dict)

        assert "queue_depth" in data
        assert isinstance(data["queue_depth"], dict)
        assert "ingestion" in data["queue_depth"]
        assert "extraction" in data["queue_depth"]
        assert isinstance(data["queue_depth"]["ingestion"], int)
        assert isinstance(data["queue_depth"]["extraction"], int)

        assert "metrics" in data
        assert isinstance(data["metrics"], dict)


def test_status_services_structure(client: TestClient, mock_system_status: SystemStatus) -> None:
    """Test GET /status services field structure.

    Verifies each service has:
    - name (str)
    - healthy (bool)
    - message (str or null)
    """
    with patch("apps.api.routes.status.get_status_use_case") as mock_get_use_case:
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = mock_system_status
        mock_get_use_case.return_value = mock_use_case

        response = client.get("/status")
        data = response.json()

        services = data["services"]
        assert len(services) > 0  # Should have at least one service

        # Check each service has required fields
        for service_name, service_data in services.items():
            assert isinstance(service_name, str)
            assert "name" in service_data
            assert "healthy" in service_data
            assert "message" in service_data
            assert isinstance(service_data["name"], str)
            assert isinstance(service_data["healthy"], bool)
            assert service_data["message"] is None or isinstance(service_data["message"], str)


def test_status_metrics_structure(client: TestClient, mock_system_status: SystemStatus) -> None:
    """Test GET /status metrics field structure.

    Verifies metrics contains:
    - documents_ingested (int >= 0)
    - chunks_indexed (int >= 0)
    - extraction_jobs_completed (int >= 0)
    - graph_nodes_created (int >= 0)
    """
    with patch("apps.api.routes.status.get_status_use_case") as mock_get_use_case:
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = mock_system_status
        mock_get_use_case.return_value = mock_use_case

        response = client.get("/status")
        data = response.json()

        metrics = data["metrics"]
        assert "documents_ingested" in metrics
        assert "chunks_indexed" in metrics
        assert "extraction_jobs_completed" in metrics
        assert "graph_nodes_created" in metrics

        assert isinstance(metrics["documents_ingested"], int)
        assert isinstance(metrics["chunks_indexed"], int)
        assert isinstance(metrics["extraction_jobs_completed"], int)
        assert isinstance(metrics["graph_nodes_created"], int)

        assert metrics["documents_ingested"] >= 0
        assert metrics["chunks_indexed"] >= 0
        assert metrics["extraction_jobs_completed"] >= 0
        assert metrics["graph_nodes_created"] >= 0


def test_status_queue_depth_non_negative(
    client: TestClient, mock_system_status: SystemStatus
) -> None:
    """Test GET /status queue depths are non-negative.

    Verifies:
    - ingestion >= 0
    - extraction >= 0
    """
    with patch("apps.api.routes.status.get_status_use_case") as mock_get_use_case:
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = mock_system_status
        mock_get_use_case.return_value = mock_use_case

        response = client.get("/status")
        data = response.json()

        queue_depth = data["queue_depth"]
        assert queue_depth["ingestion"] >= 0
        assert queue_depth["extraction"] >= 0


def test_status_same_as_extract_status(
    client: TestClient, mock_system_status: SystemStatus
) -> None:
    """Test GET /status returns same data as GET /extract/status.

    Verifies both endpoints return identical system status.
    """
    with (
        patch("apps.api.routes.status.get_status_use_case") as mock_status_use_case,
        patch("apps.api.routes.extract.get_status_use_case") as mock_extract_use_case,
    ):
        # Setup same mock for both endpoints
        mock_status_uc = AsyncMock()
        mock_status_uc.execute.return_value = mock_system_status
        mock_status_use_case.return_value = mock_status_uc

        mock_extract_uc = AsyncMock()
        mock_extract_uc.execute.return_value = mock_system_status
        mock_extract_use_case.return_value = mock_extract_uc

        status_response = client.get("/status")
        extract_status_response = client.get("/extract/status")

        assert status_response.status_code == status.HTTP_200_OK
        assert extract_status_response.status_code == status.HTTP_200_OK

        # Both should return the same data structure
        status_data = status_response.json()
        extract_status_data = extract_status_response.json()

        # Compare all top-level fields
        assert status_data["overall_healthy"] == extract_status_data["overall_healthy"]
        assert status_data["queue_depth"] == extract_status_data["queue_depth"]
        assert status_data["metrics"] == extract_status_data["metrics"]

        # Services should have same names and structure
        assert set(status_data["services"].keys()) == set(extract_status_data["services"].keys())
