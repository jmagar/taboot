"""Tests for PostgreSQL ingestion job store."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from packages.ingest.postgres_job_store import PostgresJobStore
from packages.schemas.models import IngestionJob, JobState, SourceType


@pytest.fixture
def job_store(postgres_conn):
    """Create PostgresJobStore instance with test connection."""
    return PostgresJobStore(postgres_conn)


def test_create_job(job_store):
    """Test creating an ingestion job."""
    job = IngestionJob(
        job_id=uuid4(),
        source_type=SourceType.WEB,
        source_target="https://example.com",
        state=JobState.PENDING,
        created_at=datetime.now(UTC),
        started_at=None,
        completed_at=None,
        pages_processed=0,
        chunks_created=0,
        errors=None,
    )

    job_store.create(job)

    retrieved = job_store.get_by_id(job.job_id)
    assert retrieved is not None
    assert retrieved.job_id == job.job_id
    assert retrieved.source_type == SourceType.WEB
    assert retrieved.state == JobState.PENDING
