"""Tests for IngestionJob domain model.

Tests job state transitions and metadata tracking per data-model.md:
- pending → running (job starts)
- running → completed (success)
- running → failed (error after retries)
- Track: pages_processed, chunks_created, errors[]
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from packages.schemas.models import IngestionJob, JobState, SourceType


class TestIngestionJobStateTransitions:
    """Test IngestionJob state transitions."""

    def test_create_job_starts_in_pending_state(self) -> None:
        """Test that a new job starts in PENDING state."""
        job = IngestionJob(
            job_id=uuid4(),
            source_type=SourceType.WEB,
            source_target="https://example.com",
            state=JobState.PENDING,
            created_at=datetime.now(timezone.utc),
            pages_processed=0,
            chunks_created=0,
        )

        assert job.state == JobState.PENDING
        assert job.started_at is None
        assert job.completed_at is None
        assert job.pages_processed == 0
        assert job.chunks_created == 0
        assert job.errors is None

    def test_transition_to_running_sets_started_at(self) -> None:
        """Test transition from PENDING to RUNNING sets started_at."""
        created_at = datetime.now(timezone.utc)
        job = IngestionJob(
            job_id=uuid4(),
            source_type=SourceType.WEB,
            source_target="https://example.com",
            state=JobState.PENDING,
            created_at=created_at,
            pages_processed=0,
            chunks_created=0,
        )

        # Transition to RUNNING
        started_at = datetime.now(timezone.utc)
        running_job = job.model_copy(update={"state": JobState.RUNNING, "started_at": started_at})

        assert running_job.state == JobState.RUNNING
        assert running_job.started_at == started_at
        assert running_job.started_at >= created_at
        assert running_job.completed_at is None

    def test_transition_to_completed_sets_completed_at(self) -> None:
        """Test transition from RUNNING to COMPLETED sets completed_at."""
        created_at = datetime.now(timezone.utc)
        started_at = datetime.now(timezone.utc)
        job = IngestionJob(
            job_id=uuid4(),
            source_type=SourceType.WEB,
            source_target="https://example.com",
            state=JobState.RUNNING,
            created_at=created_at,
            started_at=started_at,
            pages_processed=5,
            chunks_created=42,
        )

        # Transition to COMPLETED
        completed_at = datetime.now(timezone.utc)
        completed_job = job.model_copy(
            update={"state": JobState.COMPLETED, "completed_at": completed_at}
        )

        assert completed_job.state == JobState.COMPLETED
        assert completed_job.completed_at == completed_at
        assert completed_job.completed_at >= completed_job.started_at
        assert completed_job.pages_processed == 5
        assert completed_job.chunks_created == 42

    def test_transition_to_failed_sets_completed_at_and_errors(self) -> None:
        """Test transition from RUNNING to FAILED sets completed_at and errors."""
        created_at = datetime.now(timezone.utc)
        started_at = datetime.now(timezone.utc)
        job = IngestionJob(
            job_id=uuid4(),
            source_type=SourceType.WEB,
            source_target="https://example.com",
            state=JobState.RUNNING,
            created_at=created_at,
            started_at=started_at,
            pages_processed=2,
            chunks_created=10,
        )

        # Transition to FAILED
        completed_at = datetime.now(timezone.utc)
        errors = [{"error": "Connection timeout", "url": "https://example.com/page"}]
        failed_job = job.model_copy(
            update={"state": JobState.FAILED, "completed_at": completed_at, "errors": errors}
        )

        assert failed_job.state == JobState.FAILED
        assert failed_job.completed_at == completed_at
        assert failed_job.errors == errors
        assert len(failed_job.errors) == 1

    def test_track_pages_processed_increment(self) -> None:
        """Test that pages_processed can be incremented."""
        job = IngestionJob(
            job_id=uuid4(),
            source_type=SourceType.WEB,
            source_target="https://example.com",
            state=JobState.RUNNING,
            created_at=datetime.now(timezone.utc),
            started_at=datetime.now(timezone.utc),
            pages_processed=0,
            chunks_created=0,
        )

        # Process 3 pages
        updated_job = job.model_copy(update={"pages_processed": job.pages_processed + 3})
        assert updated_job.pages_processed == 3

        # Process 2 more pages
        updated_job = updated_job.model_copy(
            update={"pages_processed": updated_job.pages_processed + 2}
        )
        assert updated_job.pages_processed == 5

    def test_track_chunks_created_increment(self) -> None:
        """Test that chunks_created can be incremented."""
        job = IngestionJob(
            job_id=uuid4(),
            source_type=SourceType.WEB,
            source_target="https://example.com",
            state=JobState.RUNNING,
            created_at=datetime.now(timezone.utc),
            started_at=datetime.now(timezone.utc),
            pages_processed=0,
            chunks_created=0,
        )

        # Create 10 chunks
        updated_job = job.model_copy(update={"chunks_created": job.chunks_created + 10})
        assert updated_job.chunks_created == 10

        # Create 5 more chunks
        updated_job = updated_job.model_copy(
            update={"chunks_created": updated_job.chunks_created + 5}
        )
        assert updated_job.chunks_created == 15

    def test_accumulate_errors_during_processing(self) -> None:
        """Test that errors can be accumulated during processing."""
        job = IngestionJob(
            job_id=uuid4(),
            source_type=SourceType.WEB,
            source_target="https://example.com",
            state=JobState.RUNNING,
            created_at=datetime.now(timezone.utc),
            started_at=datetime.now(timezone.utc),
            pages_processed=0,
            chunks_created=0,
        )

        # Add first error
        error1 = {"error": "Rate limit exceeded", "url": "https://example.com/page1"}
        job_with_error1 = job.model_copy(update={"errors": [error1]})
        assert len(job_with_error1.errors) == 1

        # Add second error
        error2 = {"error": "Connection timeout", "url": "https://example.com/page2"}
        job_with_errors = job_with_error1.model_copy(
            update={"errors": job_with_error1.errors + [error2]}
        )
        assert len(job_with_errors.errors) == 2
        assert job_with_errors.errors[0] == error1
        assert job_with_errors.errors[1] == error2
