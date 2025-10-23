"""Tests for ExtractionJob Pydantic model."""

import pytest
from datetime import datetime, timezone
from uuid import UUID, uuid4
from pydantic import ValidationError

from packages.schemas.models import ExtractionJob


class TestExtractionJob:
    """Test ExtractionJob model validation."""

    def test_valid_extraction_job_pending(self) -> None:
        """Test valid ExtractionJob in pending state."""
        job_id = uuid4()
        doc_id = uuid4()

        job = ExtractionJob(
            job_id=job_id,
            doc_id=doc_id,
            state="pending",
            tier_a_triples=0,
            tier_b_windows=0,
            tier_c_triples=0,
            retry_count=0,
        )

        assert job.job_id == job_id
        assert job.doc_id == doc_id
        assert job.state == "pending"
        assert job.tier_a_triples == 0
        assert job.tier_b_windows == 0
        assert job.tier_c_triples == 0
        assert job.started_at is None
        assert job.completed_at is None
        assert job.retry_count == 0
        assert job.errors is None

    def test_valid_extraction_job_completed(self) -> None:
        """Test valid ExtractionJob in completed state with metrics."""
        job_id = uuid4()
        doc_id = uuid4()
        started = datetime.now(timezone.utc)
        completed = datetime.now(timezone.utc)

        job = ExtractionJob(
            job_id=job_id,
            doc_id=doc_id,
            state="completed",
            tier_a_triples=15,
            tier_b_windows=8,
            tier_c_triples=5,
            started_at=started,
            completed_at=completed,
            retry_count=0,
        )

        assert job.state == "completed"
        assert job.tier_a_triples == 15
        assert job.tier_b_windows == 8
        assert job.tier_c_triples == 5
        assert job.started_at == started
        assert job.completed_at == completed

    def test_valid_extraction_job_failed_with_errors(self) -> None:
        """Test valid ExtractionJob in failed state with error log."""
        job_id = uuid4()
        doc_id = uuid4()
        errors = {"error": "LLM timeout", "tier": "C", "timestamp": "2025-10-21T12:00:00Z"}

        job = ExtractionJob(
            job_id=job_id,
            doc_id=doc_id,
            state="failed",
            tier_a_triples=10,
            tier_b_windows=5,
            tier_c_triples=0,
            retry_count=3,
            errors=errors,
        )

        assert job.state == "failed"
        assert job.retry_count == 3
        assert job.errors == errors

    def test_job_id_required(self) -> None:
        """Test that job_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            ExtractionJob(
                doc_id=uuid4(),
                state="pending",
                tier_a_triples=0,
                tier_b_windows=0,
                tier_c_triples=0,
                retry_count=0,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("job_id",) for e in errors)

    def test_doc_id_required(self) -> None:
        """Test that doc_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            ExtractionJob(
                job_id=uuid4(),
                state="pending",
                tier_a_triples=0,
                tier_b_windows=0,
                tier_c_triples=0,
                retry_count=0,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("doc_id",) for e in errors)

    def test_state_must_be_valid_enum(self) -> None:
        """Test that state must be one of valid enum values."""
        with pytest.raises(ValidationError) as exc_info:
            ExtractionJob(
                job_id=uuid4(),
                doc_id=uuid4(),
                state="invalid_state",
                tier_a_triples=0,
                tier_b_windows=0,
                tier_c_triples=0,
                retry_count=0,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("state",) for e in errors)

    def test_valid_state_transitions(self) -> None:
        """Test all valid state enum values."""
        states = ["pending", "tier_a_done", "tier_b_done", "tier_c_done", "completed", "failed"]

        for state in states:
            job = ExtractionJob(
                job_id=uuid4(),
                doc_id=uuid4(),
                state=state,
                tier_a_triples=0,
                tier_b_windows=0,
                tier_c_triples=0,
                retry_count=0,
            )
            assert job.state == state

    def test_tier_a_triples_non_negative(self) -> None:
        """Test that tier_a_triples must be non-negative."""
        with pytest.raises(ValidationError) as exc_info:
            ExtractionJob(
                job_id=uuid4(),
                doc_id=uuid4(),
                state="pending",
                tier_a_triples=-1,
                tier_b_windows=0,
                tier_c_triples=0,
                retry_count=0,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("tier_a_triples",) for e in errors)

    def test_tier_b_windows_non_negative(self) -> None:
        """Test that tier_b_windows must be non-negative."""
        with pytest.raises(ValidationError) as exc_info:
            ExtractionJob(
                job_id=uuid4(),
                doc_id=uuid4(),
                state="pending",
                tier_a_triples=0,
                tier_b_windows=-5,
                tier_c_triples=0,
                retry_count=0,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("tier_b_windows",) for e in errors)

    def test_tier_c_triples_non_negative(self) -> None:
        """Test that tier_c_triples must be non-negative."""
        with pytest.raises(ValidationError) as exc_info:
            ExtractionJob(
                job_id=uuid4(),
                doc_id=uuid4(),
                state="pending",
                tier_a_triples=0,
                tier_b_windows=0,
                tier_c_triples=-1,
                retry_count=0,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("tier_c_triples",) for e in errors)

    def test_retry_count_between_0_and_3(self) -> None:
        """Test that retry_count must be between 0 and 3."""
        # Valid: 0 to 3
        for count in range(4):
            job = ExtractionJob(
                job_id=uuid4(),
                doc_id=uuid4(),
                state="pending",
                tier_a_triples=0,
                tier_b_windows=0,
                tier_c_triples=0,
                retry_count=count,
            )
            assert job.retry_count == count

        # Invalid: > 3
        with pytest.raises(ValidationError) as exc_info:
            ExtractionJob(
                job_id=uuid4(),
                doc_id=uuid4(),
                state="pending",
                tier_a_triples=0,
                tier_b_windows=0,
                tier_c_triples=0,
                retry_count=4,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("retry_count",) for e in errors)

        # Invalid: < 0
        with pytest.raises(ValidationError) as exc_info:
            ExtractionJob(
                job_id=uuid4(),
                doc_id=uuid4(),
                state="pending",
                tier_a_triples=0,
                tier_b_windows=0,
                tier_c_triples=0,
                retry_count=-1,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("retry_count",) for e in errors)

    def test_started_at_before_completed_at(self) -> None:
        """Test that started_at must be before completed_at."""
        started = datetime(2025, 10, 21, 12, 0, 0, tzinfo=timezone.utc)
        completed = datetime(2025, 10, 21, 11, 0, 0, tzinfo=timezone.utc)  # Before started

        with pytest.raises(ValidationError) as exc_info:
            ExtractionJob(
                job_id=uuid4(),
                doc_id=uuid4(),
                state="completed",
                tier_a_triples=0,
                tier_b_windows=0,
                tier_c_triples=0,
                started_at=started,
                completed_at=completed,
                retry_count=0,
            )

        errors = exc_info.value.errors()
        assert any("completed_at" in str(e) for e in errors)

    def test_started_at_not_future(self) -> None:
        """Test that started_at cannot be in the future."""
        future_time = datetime(2099, 1, 1, tzinfo=timezone.utc)

        with pytest.raises(ValidationError) as exc_info:
            ExtractionJob(
                job_id=uuid4(),
                doc_id=uuid4(),
                state="tier_a_done",
                tier_a_triples=0,
                tier_b_windows=0,
                tier_c_triples=0,
                started_at=future_time,
                retry_count=0,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("started_at",) for e in errors)
