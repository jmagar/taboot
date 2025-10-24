"""Tests for /extract endpoints (T086).

Following TDD: Write tests first (RED), then implement to pass (GREEN).
This test module covers:
- POST /extract/pending - Trigger extraction for pending documents
- GET /extract/status - Get extraction status (stub)
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.api.app import app


@pytest.fixture
def client() -> TestClient:
    """Provide FastAPI test client.

    Returns:
        TestClient: Configured test client for API.
    """
    return TestClient(app)


@pytest.fixture
def mock_extract_use_case() -> AsyncMock:
    """Provide mock ExtractPendingUseCase.

    Returns:
        AsyncMock: Mock use case instance.
    """
    return AsyncMock()


@pytest.mark.unit
class TestPostExtractPendingEndpoint:
    """Test POST /extract/pending endpoint for triggering extraction."""

    def test_extract_pending_endpoint_exists(self, client: TestClient) -> None:
        """Test that POST /extract/pending endpoint exists and is accessible.

        Expected to FAIL initially (endpoint not implemented yet).
        """
        response = client.post("/extract/pending")
        # Should not be 404 or 405 (route should exist)
        assert response.status_code != 404
        assert response.status_code != 405

    def test_extract_pending_returns_200_with_stats(self, client: TestClient) -> None:
        """Test that POST /extract/pending triggers extraction and returns 200 with stats.

        Expected to FAIL initially (endpoint not implemented yet).
        """
        with patch("apps.api.routes.extract.get_extract_use_case") as mock_get_use_case:
            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = {
                "processed": 5,
                "succeeded": 4,
                "failed": 1,
            }
            mock_get_use_case.return_value = mock_use_case

            response = client.post("/extract/pending")

            assert response.status_code == 200
            data = response.json()
            assert "processed" in data
            assert "succeeded" in data
            assert "failed" in data
            assert data["processed"] == 5
            assert data["succeeded"] == 4
            assert data["failed"] == 1

    def test_extract_pending_accepts_limit_param(self, client: TestClient) -> None:
        """Test that POST /extract/pending accepts optional limit query parameter.

        Expected to FAIL initially (endpoint not implemented yet).
        """
        with patch("apps.api.routes.extract.get_extract_use_case") as mock_get_use_case:
            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = {
                "processed": 10,
                "succeeded": 10,
                "failed": 0,
            }
            mock_get_use_case.return_value = mock_use_case

            response = client.post("/extract/pending?limit=10")

            assert response.status_code == 200
            # Verify use case was called with limit
            mock_use_case.execute.assert_called_once_with(limit=10)

    def test_extract_pending_limit_none_by_default(self, client: TestClient) -> None:
        """Test that limit defaults to None when not provided.

        Expected to FAIL initially (endpoint not implemented yet).
        """
        with patch("apps.api.routes.extract.get_extract_use_case") as mock_get_use_case:
            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = {
                "processed": 0,
                "succeeded": 0,
                "failed": 0,
            }
            mock_get_use_case.return_value = mock_use_case

            response = client.post("/extract/pending")

            assert response.status_code == 200
            # Verify use case was called with limit=None
            mock_use_case.execute.assert_called_once_with(limit=None)

    def test_extract_pending_validates_limit_positive(self, client: TestClient) -> None:
        """Test that limit must be a positive integer.

        Expected to FAIL initially (endpoint not implemented yet).
        """
        response = client.post("/extract/pending?limit=0")
        # Should reject with 422 Unprocessable Entity
        assert response.status_code == 422

        response = client.post("/extract/pending?limit=-5")
        assert response.status_code == 422

    def test_extract_pending_returns_500_on_error(self, client: TestClient) -> None:
        """Test that POST /extract/pending returns 500 on internal errors.

        Expected to FAIL initially (endpoint not implemented yet).
        """
        with patch("apps.api.routes.extract.get_extract_use_case") as mock_get_use_case:
            mock_use_case = AsyncMock()
            mock_use_case.execute.side_effect = RuntimeError("Database connection failed")
            mock_get_use_case.return_value = mock_use_case

            response = client.post("/extract/pending")

            assert response.status_code == 500
            data = response.json()
            assert "detail" in data or "error" in data

    def test_extract_pending_response_includes_all_fields(self, client: TestClient) -> None:
        """Test that response includes all required fields: processed, succeeded, failed.

        Expected to FAIL initially (endpoint not implemented yet).
        """
        with patch("apps.api.routes.extract.get_extract_use_case") as mock_get_use_case:
            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = {
                "processed": 15,
                "succeeded": 12,
                "failed": 3,
            }
            mock_get_use_case.return_value = mock_use_case

            response = client.post("/extract/pending")

            assert response.status_code == 200
            data = response.json()

            # Verify all required fields exist
            assert "processed" in data
            assert "succeeded" in data
            assert "failed" in data

            # Verify field types are integers
            assert isinstance(data["processed"], int)
            assert isinstance(data["succeeded"], int)
            assert isinstance(data["failed"], int)


@pytest.mark.unit
class TestGetExtractStatusEndpoint:
    """Test GET /extract/status endpoint for extraction status."""

    def test_extract_status_endpoint_exists(self, client: TestClient) -> None:
        """Test that GET /extract/status endpoint exists.

        Expected to FAIL initially (endpoint not implemented yet).
        """
        response = client.get("/extract/status")
        # Should not be 404 or 405
        assert response.status_code != 404
        assert response.status_code != 405

    def test_extract_status_returns_200_with_stub_data(self, client: TestClient) -> None:
        """Test that GET /extract/status returns 200 with stub status data."""
        from packages.core.use_cases.get_status import (
            MetricsSnapshot,
            QueueDepth,
            SystemStatus,
        )

        # Mock the use case factory function
        with patch("apps.api.routes.extract.get_status_use_case") as mock_get_use_case:
            # Setup mock use case
            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = SystemStatus(
                overall_healthy=True,
                services={},
                queue_depth=QueueDepth(ingestion=0, extraction=0),
                metrics=MetricsSnapshot(
                    documents_ingested=0,
                    chunks_indexed=0,
                    extraction_jobs_completed=0,
                    graph_nodes_created=0,
                ),
            )
            mock_get_use_case.return_value = mock_use_case

            response = client.get("/extract/status")

            assert response.status_code == 200
            data = response.json()

            # Verify stub fields exist
            assert "overall_healthy" in data
            assert "queue_depth" in data

    def test_extract_status_stub_returns_ready(self, client: TestClient) -> None:
        """Test that stub status returns 'ready' and queue_depth 0."""
        from packages.core.use_cases.get_status import (
            MetricsSnapshot,
            QueueDepth,
            SystemStatus,
        )

        # Mock the use case factory function
        with patch("apps.api.routes.extract.get_status_use_case") as mock_get_use_case:
            # Setup mock use case
            mock_use_case = AsyncMock()
            mock_use_case.execute.return_value = SystemStatus(
                overall_healthy=True,
                services={},
                queue_depth=QueueDepth(ingestion=0, extraction=0),
                metrics=MetricsSnapshot(
                    documents_ingested=0,
                    chunks_indexed=0,
                    extraction_jobs_completed=0,
                    graph_nodes_created=0,
                ),
            )
            mock_get_use_case.return_value = mock_use_case

            response = client.get("/extract/status")

            assert response.status_code == 200
            data = response.json()

            # Verify stub values
            assert data.get("overall_healthy") is True
            assert data.get("queue_depth") is not None
            assert data["queue_depth"]["ingestion"] == 0
            assert data["queue_depth"]["extraction"] == 0
