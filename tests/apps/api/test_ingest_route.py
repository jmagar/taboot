"""Tests for /ingest endpoints (T053-T054).

Following TDD: Write tests first (RED), then implement to pass (GREEN).
This test module covers:
- POST /ingest - Start ingestion job
- GET /ingest/{job_id} - Get job status
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from apps.api.app import app
from packages.schemas.models import IngestionJob, JobState, SourceType


@pytest.fixture
def client() -> TestClient:
    """Provide FastAPI test client.

    Returns:
        TestClient: Configured test client for API.
    """
    return TestClient(app)


@pytest.fixture
def mock_ingest_use_case() -> Mock:
    """Provide mock IngestWebUseCase.

    Returns:
        Mock: Mock use case instance.
    """
    return Mock()


@pytest.fixture
def sample_job() -> IngestionJob:
    """Provide sample IngestionJob for testing.

    Returns:
        IngestionJob: Sample job in PENDING state.
    """
    return IngestionJob(
        job_id=uuid4(),
        source_type=SourceType.WEB,
        source_target="https://example.com",
        state=JobState.PENDING,
        created_at=datetime.now(UTC),
        pages_processed=0,
        chunks_created=0,
    )


@pytest.fixture
def completed_job() -> IngestionJob:
    """Provide completed IngestionJob for testing.

    Returns:
        IngestionJob: Sample job in COMPLETED state.
    """
    job_id = uuid4()
    created = datetime.now(UTC)
    return IngestionJob(
        job_id=job_id,
        source_type=SourceType.WEB,
        source_target="https://example.com",
        state=JobState.COMPLETED,
        created_at=created,
        started_at=created,
        completed_at=created,
        pages_processed=18,
        chunks_created=342,
        errors=None,
    )


@pytest.mark.unit
class TestPostIngestEndpoint:
    """Test POST /ingest endpoint for creating ingestion jobs."""

    def test_ingest_endpoint_exists(self, client: TestClient) -> None:
        """Test that POST /ingest endpoint exists and is accessible.

        Expected to FAIL initially (endpoint not implemented yet).
        """
        # Missing required fields should trigger 422, not 404
        response = client.post("/ingest", json={})
        assert response.status_code != 404

    def test_ingest_creates_job_returns_202(
        self, client: TestClient, sample_job: IngestionJob
    ) -> None:
        """Test that POST /ingest creates job and returns 202 Accepted.

        Expected to FAIL initially (endpoint not implemented yet).
        """
        with patch(
            "apps.api.routes.ingest.get_ingest_use_case"
        ) as mock_get_use_case:
            mock_use_case = Mock()
            mock_use_case.execute.return_value = sample_job
            mock_get_use_case.return_value = mock_use_case

            response = client.post(
                "/ingest",
                json={
                    "source_type": "web",
                    "source_target": "https://example.com",
                    "limit": 20,
                },
            )

            assert response.status_code == 202
            data = response.json()
            assert "job_id" in data
            assert "state" in data
            assert "created_at" in data
            assert data["state"] == "pending"

    def test_ingest_validates_source_type(self, client: TestClient) -> None:
        """Test that POST /ingest validates source_type enum.

        Expected to FAIL initially (endpoint not implemented yet).
        """
        response = client.post(
            "/ingest",
            json={
                "source_type": "invalid_type",
                "source_target": "https://example.com",
            },
        )

        assert response.status_code == 422  # Unprocessable Entity
        data = response.json()
        assert "detail" in data

    def test_ingest_requires_source_target(self, client: TestClient) -> None:
        """Test that POST /ingest requires source_target field.

        Expected to FAIL initially (endpoint not implemented yet).
        """
        response = client.post(
            "/ingest",
            json={
                "source_type": "web",
            },
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_ingest_optional_limit_parameter(
        self, client: TestClient, sample_job: IngestionJob
    ) -> None:
        """Test that limit parameter is optional in POST /ingest.

        Expected to FAIL initially (endpoint not implemented yet).
        """
        with patch(
            "apps.api.routes.ingest.get_ingest_use_case"
        ) as mock_get_use_case:
            mock_use_case = Mock()
            mock_use_case.execute.return_value = sample_job
            mock_get_use_case.return_value = mock_use_case

            # Should succeed without limit
            response = client.post(
                "/ingest",
                json={
                    "source_type": "web",
                    "source_target": "https://example.com",
                },
            )

            assert response.status_code == 202
            mock_use_case.execute.assert_called_once()
            # Verify limit was passed as None
            call_kwargs = mock_use_case.execute.call_args.kwargs
            assert call_kwargs.get("limit") is None

    def test_ingest_passes_limit_to_use_case(
        self, client: TestClient, sample_job: IngestionJob
    ) -> None:
        """Test that limit parameter is passed to use case when provided.

        Expected to FAIL initially (endpoint not implemented yet).
        """
        with patch(
            "apps.api.routes.ingest.get_ingest_use_case"
        ) as mock_get_use_case:
            mock_use_case = Mock()
            mock_use_case.execute.return_value = sample_job
            mock_get_use_case.return_value = mock_use_case

            response = client.post(
                "/ingest",
                json={
                    "source_type": "web",
                    "source_target": "https://example.com",
                    "limit": 50,
                },
            )

            assert response.status_code == 202
            mock_use_case.execute.assert_called_once()
            call_kwargs = mock_use_case.execute.call_args.kwargs
            assert call_kwargs.get("limit") == 50

    def test_ingest_response_includes_all_fields(
        self, client: TestClient, sample_job: IngestionJob
    ) -> None:
        """Test that response includes all required fields per OpenAPI spec.

        Expected to FAIL initially (endpoint not implemented yet).
        """
        with patch(
            "apps.api.routes.ingest.get_ingest_use_case"
        ) as mock_get_use_case:
            mock_use_case = Mock()
            mock_use_case.execute.return_value = sample_job
            mock_get_use_case.return_value = mock_use_case

            response = client.post(
                "/ingest",
                json={
                    "source_type": "web",
                    "source_target": "https://example.com",
                },
            )

            assert response.status_code == 202
            data = response.json()
            # Verify all required response fields
            assert "job_id" in data
            assert "state" in data
            assert "source_type" in data
            assert "source_target" in data
            assert "created_at" in data

            # Verify field types
            UUID(data["job_id"])  # Should parse as valid UUID
            assert data["source_type"] == "web"
            assert data["source_target"] == "https://example.com"
            datetime.fromisoformat(
                data["created_at"].replace("Z", "+00:00")
            )  # Valid ISO datetime


@pytest.mark.unit
class TestGetIngestStatusEndpoint:
    """Test GET /ingest/{job_id} endpoint for retrieving job status."""

    def test_get_status_endpoint_exists(self, client: TestClient) -> None:
        """Test that GET /ingest/{job_id} endpoint exists.

        Expected to FAIL initially (endpoint not implemented yet).
        """
        job_id = uuid4()
        response = client.get(f"/ingest/{job_id}")
        # Should not be 404 for route existence (might be 404 for job not found)
        # But definitely should not be 405 (Method Not Allowed)
        assert response.status_code != 405

    def test_get_status_returns_job_details(
        self, client: TestClient, completed_job: IngestionJob
    ) -> None:
        """Test that GET /ingest/{job_id} returns complete job details.

        Expected to FAIL initially (endpoint not implemented yet).
        """
        with patch("apps.api.routes.ingest.get_job_store") as mock_get_store:
            mock_store = MagicMock()
            mock_store.get_by_id.return_value = completed_job
            mock_get_store.return_value = mock_store

            response = client.get(f"/ingest/{completed_job.job_id}")

            assert response.status_code == 200
            data = response.json()

            # Verify all status fields
            assert data["job_id"] == str(completed_job.job_id)
            assert data["state"] == "completed"
            assert data["source_type"] == "web"
            assert data["source_target"] == "https://example.com"
            assert data["pages_processed"] == 18
            assert data["chunks_created"] == 342
            assert "created_at" in data
            assert "started_at" in data
            assert "completed_at" in data

    def test_get_status_job_not_found_returns_404(
        self, client: TestClient
    ) -> None:
        """Test that GET /ingest/{job_id} returns 404 for missing job.

        Expected to FAIL initially (endpoint not implemented yet).
        """
        with patch("apps.api.routes.ingest.get_job_store") as mock_get_store:
            mock_store = MagicMock()
            mock_store.get_by_id.return_value = None
            mock_get_store.return_value = mock_store

            job_id = uuid4()
            response = client.get(f"/ingest/{job_id}")

            assert response.status_code == 404
            data = response.json()
            assert "detail" in data or "error" in data

    def test_get_status_validates_job_id_format(
        self, client: TestClient
    ) -> None:
        """Test that GET /ingest/{job_id} validates UUID format.

        Expected to FAIL initially (endpoint not implemented yet).
        """
        response = client.get("/ingest/not-a-valid-uuid")

        assert response.status_code == 422  # Unprocessable Entity
        data = response.json()
        assert "detail" in data

    def test_get_status_includes_error_details(
        self, client: TestClient, sample_job: IngestionJob
    ) -> None:
        """Test that failed jobs include error details in response.

        Expected to FAIL initially (endpoint not implemented yet).
        """
        # Create failed job with errors
        failed_job = sample_job.model_copy(
            update={
                "state": JobState.FAILED,
                "errors": [
                    {
                        "error": "Connection timeout",
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                ],
            }
        )

        with patch("apps.api.routes.ingest.get_job_store") as mock_get_store:
            mock_store = MagicMock()
            mock_store.get_by_id.return_value = failed_job
            mock_get_store.return_value = mock_store

            response = client.get(f"/ingest/{failed_job.job_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["state"] == "failed"
            assert "errors" in data
            assert len(data["errors"]) == 1
            assert data["errors"][0]["error"] == "Connection timeout"

    def test_get_status_null_timestamps_for_pending_job(
        self, client: TestClient, sample_job: IngestionJob
    ) -> None:
        """Test that pending jobs have null started_at and completed_at.

        Expected to FAIL initially (endpoint not implemented yet).
        """
        with patch("apps.api.routes.ingest.get_job_store") as mock_get_store:
            mock_store = MagicMock()
            mock_store.get_by_id.return_value = sample_job
            mock_get_store.return_value = mock_store

            response = client.get(f"/ingest/{sample_job.job_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["state"] == "pending"
            assert data["started_at"] is None
            assert data["completed_at"] is None
