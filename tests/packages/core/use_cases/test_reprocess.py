"""Tests for ReprocessUseCase.

Tests document reprocessing with date filtering.
Following TDD methodology (RED-GREEN-REFACTOR).
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from uuid import uuid4

import pytest

from packages.schemas.models import Document, ExtractionState


class TestReprocessUseCase:
    """Tests for the ReprocessUseCase class."""

    def test_reprocess_queues_documents_by_date(self) -> None:
        """Test that reprocess queues documents modified after specified date."""
        from packages.core.use_cases.reprocess import ReprocessUseCase

        # Create mock document store
        document_store = Mock()

        # Mock documents from last 7 days
        since_date = datetime.now(UTC) - timedelta(days=7)
        mock_docs = [
            Document(
                doc_id=uuid4(),
                source_url="https://example.com/doc1",
                source_type="web",
                content_hash="a" * 64,  # SHA-256 is exactly 64 hex chars
                ingested_at=datetime.now(UTC) - timedelta(days=3),
                extraction_state=ExtractionState.COMPLETED,
                updated_at=datetime.now(UTC),
            ),
            Document(
                doc_id=uuid4(),
                source_url="https://example.com/doc2",
                source_type="web",
                content_hash="b" * 64,  # SHA-256 is exactly 64 hex chars
                ingested_at=datetime.now(UTC) - timedelta(days=5),
                extraction_state=ExtractionState.COMPLETED,
                updated_at=datetime.now(UTC),
            ),
        ]
        document_store.query_by_date.return_value = mock_docs

        # Create use case
        use_case = ReprocessUseCase(document_store=document_store)

        # Execute
        result = use_case.execute(since_date=since_date)

        # Verify
        document_store.query_by_date.assert_called_once_with(since_date=since_date)
        assert result["documents_queued"] == 2

    def test_reprocess_resets_extraction_state(self) -> None:
        """Test that reprocess resets extraction_state to PENDING."""
        from packages.core.use_cases.reprocess import ReprocessUseCase

        document_store = Mock()

        since_date = datetime.now(UTC) - timedelta(days=7)
        mock_doc = Document(
            doc_id=uuid4(),
            source_url="https://example.com/doc",
            source_type="web",
            content_hash="c" * 64,  # SHA-256 is exactly 64 hex chars
            ingested_at=datetime.now(UTC) - timedelta(days=3),
            extraction_state=ExtractionState.COMPLETED,
            updated_at=datetime.now(UTC),
        )
        document_store.query_by_date.return_value = [mock_doc]

        use_case = ReprocessUseCase(document_store=document_store)
        result = use_case.execute(since_date=since_date)

        # Verify document state was reset to PENDING
        assert document_store.update_document.called
        updated_doc = document_store.update_document.call_args[0][0]
        assert updated_doc.extraction_state == ExtractionState.PENDING
        assert result["documents_queued"] == 1

    def test_reprocess_handles_empty_result(self) -> None:
        """Test that reprocess handles no documents gracefully."""
        from packages.core.use_cases.reprocess import ReprocessUseCase

        document_store = Mock()
        document_store.query_by_date.return_value = []

        since_date = datetime.now(UTC) - timedelta(days=7)
        use_case = ReprocessUseCase(document_store=document_store)
        result = use_case.execute(since_date=since_date)

        assert result["documents_queued"] == 0

    def test_reprocess_validates_date(self) -> None:
        """Test that reprocess validates since_date is not in future."""
        from packages.core.use_cases.reprocess import ReprocessUseCase

        document_store = Mock()
        use_case = ReprocessUseCase(document_store=document_store)

        # Future date should raise error
        future_date = datetime.now(UTC) + timedelta(days=1)
        with pytest.raises(ValueError, match="future"):
            use_case.execute(since_date=future_date)
