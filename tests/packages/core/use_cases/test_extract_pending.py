"""Tests for ExtractPendingUseCase.

Validates the extraction use-case orchestrates document extraction properly:
- Queries pending documents from store
- Calls ExtractionOrchestrator for each document
- Updates document extraction state based on results
- Handles per-document errors gracefully
"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from packages.core.use_cases.extract_pending import ExtractPendingUseCase
from packages.schemas.models import Document, ExtractionJob, ExtractionState, SourceType


@pytest.mark.unit
def test_extract_pending_processes_documents() -> None:
    """Test that extract_pending processes all pending documents."""
    # Setup: Create 3 pending documents
    doc1 = Document(
        doc_id=uuid4(),
        source_url="https://example.com/doc1",
        source_type=SourceType.WEB,
        content_hash="a" * 64,
        ingested_at=datetime.now(UTC),
        extraction_state=ExtractionState.PENDING,
        updated_at=datetime.now(UTC),
    )
    doc2 = Document(
        doc_id=uuid4(),
        source_url="https://example.com/doc2",
        source_type=SourceType.WEB,
        content_hash="b" * 64,
        ingested_at=datetime.now(UTC),
        extraction_state=ExtractionState.PENDING,
        updated_at=datetime.now(UTC),
    )
    doc3 = Document(
        doc_id=uuid4(),
        source_url="https://example.com/doc3",
        source_type=SourceType.WEB,
        content_hash="c" * 64,
        ingested_at=datetime.now(UTC),
        extraction_state=ExtractionState.PENDING,
        updated_at=datetime.now(UTC),
    )

    # Mock document store (returns 3 pending documents)
    mock_doc_store = MagicMock()
    mock_doc_store.query_pending.return_value = [doc1, doc2, doc3]
    mock_doc_store.get_content.side_effect = [
        "Content for doc1",
        "Content for doc2",
        "Content for doc3",
    ]

    # Mock orchestrator (returns successful jobs for doc1 and doc2, failed for doc3)
    mock_orchestrator = MagicMock()
    job1 = ExtractionJob(
        job_id=uuid4(),
        doc_id=doc1.doc_id,
        state=ExtractionState.COMPLETED,
        tier_a_triples=5,
        tier_b_windows=3,
        tier_c_triples=10,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        retry_count=0,
    )
    job2 = ExtractionJob(
        job_id=uuid4(),
        doc_id=doc2.doc_id,
        state=ExtractionState.COMPLETED,
        tier_a_triples=3,
        tier_b_windows=2,
        tier_c_triples=7,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        retry_count=0,
    )
    job3 = ExtractionJob(
        job_id=uuid4(),
        doc_id=doc3.doc_id,
        state=ExtractionState.FAILED,
        tier_a_triples=0,
        tier_b_windows=0,
        tier_c_triples=0,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        retry_count=3,
        errors={"error": "LLM timeout"},
    )

    # Convert async mock returns to coroutines
    async def mock_process_doc1(doc_id: object, content: str) -> ExtractionJob:
        return job1

    async def mock_process_doc2(doc_id: object, content: str) -> ExtractionJob:
        return job2

    async def mock_process_doc3(doc_id: object, content: str) -> ExtractionJob:
        return job3

    mock_orchestrator.process_document.side_effect = [
        mock_process_doc1(doc1.doc_id, "Content for doc1"),
        mock_process_doc2(doc2.doc_id, "Content for doc2"),
        mock_process_doc3(doc3.doc_id, "Content for doc3"),
    ]

    # Create use-case
    use_case = ExtractPendingUseCase(
        orchestrator=mock_orchestrator,
        document_store=mock_doc_store,
    )

    # Execute
    result = asyncio.run(use_case.execute())

    # Assert: orchestrator called 3 times
    assert mock_orchestrator.process_document.call_count == 3

    # Assert: document store updated 3 times
    assert mock_doc_store.update_document.call_count == 3

    # Assert: summary returned correctly
    assert result == {
        "processed": 3,
        "succeeded": 2,
        "failed": 1,
    }


@pytest.mark.unit
def test_extract_pending_handles_limit() -> None:
    """Test that extract_pending respects limit parameter."""
    # Setup: Create 5 pending documents
    docs = [
        Document(
            doc_id=uuid4(),
            source_url=f"https://example.com/doc{i}",
            source_type=SourceType.WEB,
            content_hash=f"{i}" * 64,
            ingested_at=datetime.now(UTC),
            extraction_state=ExtractionState.PENDING,
            updated_at=datetime.now(UTC),
        )
        for i in range(5)
    ]

    # Mock document store (returns only 2 documents when limit=2)
    mock_doc_store = MagicMock()
    mock_doc_store.query_pending.return_value = docs[:2]
    mock_doc_store.get_content.side_effect = [f"Content for doc{i}" for i in range(2)]

    # Mock orchestrator (returns successful jobs)
    mock_orchestrator = MagicMock()

    async def mock_process_doc(doc_id: object, content: str) -> ExtractionJob:
        from uuid import UUID

        return ExtractionJob(
            job_id=uuid4(),
            doc_id=doc_id if isinstance(doc_id, UUID) else uuid4(),
            state=ExtractionState.COMPLETED,
            tier_a_triples=1,
            tier_b_windows=1,
            tier_c_triples=1,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            retry_count=0,
        )

    mock_orchestrator.process_document.side_effect = [
        mock_process_doc(docs[0].doc_id, "Content for doc0"),
        mock_process_doc(docs[1].doc_id, "Content for doc1"),
    ]

    # Create use-case
    use_case = ExtractPendingUseCase(
        orchestrator=mock_orchestrator,
        document_store=mock_doc_store,
    )

    # Execute with limit=2
    result = asyncio.run(use_case.execute(limit=2))

    # Assert: query_pending called with limit=2
    mock_doc_store.query_pending.assert_called_once_with(limit=2)

    # Assert: only 2 documents processed
    assert result["processed"] == 2


@pytest.mark.unit
def test_extract_pending_continues_on_individual_failure() -> None:
    """Test that extract_pending continues processing when one document fails."""
    # Setup: Create 3 pending documents
    docs = [
        Document(
            doc_id=uuid4(),
            source_url=f"https://example.com/doc{i}",
            source_type=SourceType.WEB,
            content_hash=f"{i}" * 64,
            ingested_at=datetime.now(UTC),
            extraction_state=ExtractionState.PENDING,
            updated_at=datetime.now(UTC),
        )
        for i in range(3)
    ]

    # Mock document store
    mock_doc_store = MagicMock()
    mock_doc_store.query_pending.return_value = docs
    mock_doc_store.get_content.side_effect = [
        "Content for doc0",
        "Content for doc1",
        "Content for doc2",
    ]

    # Mock orchestrator: doc1 raises exception, others succeed
    mock_orchestrator = MagicMock()

    async def mock_process_success(doc_id: object, content: str) -> ExtractionJob:
        from uuid import UUID

        return ExtractionJob(
            job_id=uuid4(),
            doc_id=doc_id if isinstance(doc_id, UUID) else uuid4(),
            state=ExtractionState.COMPLETED,
            tier_a_triples=1,
            tier_b_windows=1,
            tier_c_triples=1,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            retry_count=0,
        )

    async def mock_process_failure(doc_id: object, content: str) -> ExtractionJob:
        raise RuntimeError("Extraction failed for doc1")

    mock_orchestrator.process_document.side_effect = [
        mock_process_success(docs[0].doc_id, "Content for doc0"),
        mock_process_failure(docs[1].doc_id, "Content for doc1"),
        mock_process_success(docs[2].doc_id, "Content for doc2"),
    ]

    # Create use-case
    use_case = ExtractPendingUseCase(
        orchestrator=mock_orchestrator,
        document_store=mock_doc_store,
    )

    # Execute
    result = asyncio.run(use_case.execute())

    # Assert: all 3 documents attempted
    assert mock_orchestrator.process_document.call_count == 3

    # Assert: 2 succeeded, 1 failed
    assert result == {
        "processed": 3,
        "succeeded": 2,
        "failed": 1,
    }


@pytest.mark.unit
def test_extract_pending_handles_empty_queue() -> None:
    """Test that extract_pending handles empty queue gracefully."""
    # Mock document store (returns empty list)
    mock_doc_store = MagicMock()
    mock_doc_store.query_pending.return_value = []

    # Mock orchestrator (should not be called)
    mock_orchestrator = MagicMock()

    # Create use-case
    use_case = ExtractPendingUseCase(
        orchestrator=mock_orchestrator,
        document_store=mock_doc_store,
    )

    # Execute
    result = asyncio.run(use_case.execute())

    # Assert: orchestrator not called
    assert mock_orchestrator.process_document.call_count == 0

    # Assert: summary returned with zeros
    assert result == {
        "processed": 0,
        "succeeded": 0,
        "failed": 0,
    }


@pytest.mark.unit
def test_extract_pending_updates_extraction_state() -> None:
    """Test that extract_pending updates document extraction state correctly."""
    # Setup: Create pending document
    doc = Document(
        doc_id=uuid4(),
        source_url="https://example.com/doc",
        source_type=SourceType.WEB,
        content_hash="a" * 64,
        ingested_at=datetime.now(UTC),
        extraction_state=ExtractionState.PENDING,
        updated_at=datetime.now(UTC),
    )

    # Mock document store
    mock_doc_store = MagicMock()
    mock_doc_store.query_pending.return_value = [doc]
    mock_doc_store.get_content.return_value = "Content for doc"

    # Mock orchestrator (returns completed job)
    mock_orchestrator = MagicMock()
    job = ExtractionJob(
        job_id=uuid4(),
        doc_id=doc.doc_id,
        state=ExtractionState.COMPLETED,
        tier_a_triples=5,
        tier_b_windows=3,
        tier_c_triples=10,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        retry_count=0,
    )

    async def mock_process_doc(doc_id: object, content: str) -> ExtractionJob:
        return job

    mock_orchestrator.process_document.return_value = mock_process_doc(
        doc.doc_id, "Content for doc"
    )

    # Create use-case
    use_case = ExtractPendingUseCase(
        orchestrator=mock_orchestrator,
        document_store=mock_doc_store,
    )

    # Execute
    asyncio.run(use_case.execute())

    # Assert: update_document called with correct state
    assert mock_doc_store.update_document.call_count == 1
    updated_doc = mock_doc_store.update_document.call_args[0][0]
    assert updated_doc.extraction_state == ExtractionState.COMPLETED
