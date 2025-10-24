"""Test persistent job storage in ingestion API."""

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from apps.api.app import app


@pytest.fixture
def client() -> None:
    """Create test client."""
    return TestClient(app)


def test_job_persists_across_requests(client, postgres_conn) -> None:
    """Test that jobs persist in database, not memory."""
    # Create job
    response = client.post(
        "/ingest/",
        json={
            "source_type": "web",
            "source_target": "https://example.com",
            "limit": 5,
        },
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    # Verify job exists in database
    from packages.ingest.postgres_job_store import PostgresJobStore

    job_store = PostgresJobStore(postgres_conn)
    job = job_store.get_by_id(UUID(job_id))

    assert job is not None
    assert str(job.job_id) == job_id
    assert job.source_type.value == "web"
