"""Tests for ExtractionWindow Pydantic model."""

import pytest
from datetime import datetime, timezone
from uuid import UUID, uuid4
from pydantic import ValidationError

from packages.schemas.models import ExtractionWindow


class TestExtractionWindow:
    """Test ExtractionWindow model validation."""

    def test_valid_extraction_window_tier_a(self) -> None:
        """Test valid ExtractionWindow for Tier A."""
        window_id = uuid4()
        doc_id = uuid4()
        now = datetime.now(timezone.utc)

        window = ExtractionWindow(
            window_id=window_id,
            doc_id=doc_id,
            content="Test content for extraction",
            tier="A",
            triples_generated=5,
            processed_at=now,
        )

        assert window.window_id == window_id
        assert window.doc_id == doc_id
        assert window.content == "Test content for extraction"
        assert window.tier == "A"
        assert window.triples_generated == 5
        assert window.llm_latency_ms is None
        assert window.cache_hit is None
        assert window.processed_at == now
        assert window.extraction_version is None

    def test_valid_extraction_window_tier_c_with_metrics(self) -> None:
        """Test valid ExtractionWindow for Tier C with LLM metrics."""
        window_id = uuid4()
        doc_id = uuid4()
        now = datetime.now(timezone.utc)

        window = ExtractionWindow(
            window_id=window_id,
            doc_id=doc_id,
            content="Test content for LLM extraction",
            tier="C",
            triples_generated=3,
            llm_latency_ms=250,
            cache_hit=True,
            processed_at=now,
            extraction_version="v1.2.0",
        )

        assert window.tier == "C"
        assert window.llm_latency_ms == 250
        assert window.cache_hit is True
        assert window.extraction_version == "v1.2.0"

    def test_window_id_required(self) -> None:
        """Test that window_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            ExtractionWindow(
                doc_id=uuid4(),
                content="Test",
                tier="A",
                triples_generated=0,
                processed_at=datetime.now(timezone.utc),
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("window_id",) for e in errors)

    def test_doc_id_required(self) -> None:
        """Test that doc_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            ExtractionWindow(
                window_id=uuid4(),
                content="Test",
                tier="A",
                triples_generated=0,
                processed_at=datetime.now(timezone.utc),
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("doc_id",) for e in errors)

    def test_content_required_and_non_empty(self) -> None:
        """Test that content is required and non-empty."""
        with pytest.raises(ValidationError) as exc_info:
            ExtractionWindow(
                window_id=uuid4(),
                doc_id=uuid4(),
                content="",
                tier="A",
                triples_generated=0,
                processed_at=datetime.now(timezone.utc),
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("content",) for e in errors)

    def test_content_max_length_2048(self) -> None:
        """Test that content has max length of 2048 chars."""
        with pytest.raises(ValidationError) as exc_info:
            ExtractionWindow(
                window_id=uuid4(),
                doc_id=uuid4(),
                content="x" * 2049,
                tier="A",
                triples_generated=0,
                processed_at=datetime.now(timezone.utc),
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("content",) for e in errors)

    def test_tier_must_be_a_b_or_c(self) -> None:
        """Test that tier must be A, B, or C."""
        with pytest.raises(ValidationError) as exc_info:
            ExtractionWindow(
                window_id=uuid4(),
                doc_id=uuid4(),
                content="Test",
                tier="D",
                triples_generated=0,
                processed_at=datetime.now(timezone.utc),
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("tier",) for e in errors)

    def test_triples_generated_non_negative(self) -> None:
        """Test that triples_generated must be non-negative."""
        with pytest.raises(ValidationError) as exc_info:
            ExtractionWindow(
                window_id=uuid4(),
                doc_id=uuid4(),
                content="Test",
                tier="A",
                triples_generated=-1,
                processed_at=datetime.now(timezone.utc),
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("triples_generated",) for e in errors)

    def test_llm_latency_ms_non_negative(self) -> None:
        """Test that llm_latency_ms must be non-negative if provided."""
        with pytest.raises(ValidationError) as exc_info:
            ExtractionWindow(
                window_id=uuid4(),
                doc_id=uuid4(),
                content="Test",
                tier="C",
                triples_generated=0,
                llm_latency_ms=-10,
                processed_at=datetime.now(timezone.utc),
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("llm_latency_ms",) for e in errors)

    def test_processed_at_required(self) -> None:
        """Test that processed_at is required."""
        with pytest.raises(ValidationError) as exc_info:
            ExtractionWindow(
                window_id=uuid4(),
                doc_id=uuid4(),
                content="Test",
                tier="A",
                triples_generated=0,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("processed_at",) for e in errors)

    def test_processed_at_not_future(self) -> None:
        """Test that processed_at cannot be in the future."""
        future_time = datetime(2099, 1, 1, tzinfo=timezone.utc)

        with pytest.raises(ValidationError) as exc_info:
            ExtractionWindow(
                window_id=uuid4(),
                doc_id=uuid4(),
                content="Test",
                tier="A",
                triples_generated=0,
                processed_at=future_time,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("processed_at",) for e in errors)
