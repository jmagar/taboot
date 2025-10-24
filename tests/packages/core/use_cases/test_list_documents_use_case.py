"""Tests for ListDocumentsUseCase.

Tests pagination, filtering by source_type and extraction_state per T163.
Follows TDD RED-GREEN-REFACTOR methodology.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from packages.schemas.models import Document, ExtractionState, SourceType


@pytest.fixture
def mock_db_client():
    """Mock database client for querying documents."""
    client = AsyncMock()
    return client


@pytest.fixture
def sample_documents():
    """Sample documents for testing."""
    now = datetime.now(UTC)
    return [
        Document(
            doc_id=uuid.uuid4(),
            source_url="https://example.com/doc1",
            source_type=SourceType.WEB,
            content_hash="a" * 64,
            ingested_at=now,
            extraction_state=ExtractionState.COMPLETED,
            updated_at=now,
        ),
        Document(
            doc_id=uuid.uuid4(),
            source_url="https://github.com/user/repo",
            source_type=SourceType.GITHUB,
            content_hash="b" * 64,
            ingested_at=now,
            extraction_state=ExtractionState.PENDING,
            updated_at=now,
        ),
        Document(
            doc_id=uuid.uuid4(),
            source_url="https://example.com/doc3",
            source_type=SourceType.WEB,
            content_hash="c" * 64,
            ingested_at=now,
            extraction_state=ExtractionState.TIER_A_DONE,
            updated_at=now,
        ),
    ]


@pytest.mark.asyncio
async def test_list_documents_no_filters(mock_db_client, sample_documents):
    """Test listing all documents without filters.

    RED phase: This test will fail because ListDocumentsUseCase doesn't exist yet.
    """
    from packages.core.use_cases.list_documents import ListDocumentsUseCase

    mock_db_client.fetch_documents = AsyncMock(return_value=sample_documents[:2])
    mock_db_client.count_documents = AsyncMock(return_value=3)

    use_case = ListDocumentsUseCase(db_client=mock_db_client)
    result = await use_case.execute(limit=2, offset=0)

    assert result.total == 3
    assert len(result.documents) == 2
    assert result.limit == 2
    assert result.offset == 0
    mock_db_client.fetch_documents.assert_called_once_with(
        limit=2, offset=0, source_type=None, extraction_state=None
    )


@pytest.mark.asyncio
async def test_list_documents_filter_by_source_type(mock_db_client, sample_documents):
    """Test filtering documents by source_type.

    RED phase: Will fail until implementation exists.
    """
    from packages.core.use_cases.list_documents import ListDocumentsUseCase

    web_docs = [d for d in sample_documents if d.source_type == SourceType.WEB]
    mock_db_client.fetch_documents = AsyncMock(return_value=web_docs)
    mock_db_client.count_documents = AsyncMock(return_value=len(web_docs))

    use_case = ListDocumentsUseCase(db_client=mock_db_client)
    result = await use_case.execute(limit=10, offset=0, source_type=SourceType.WEB)

    assert result.total == 2
    assert len(result.documents) == 2
    assert all(d.source_type == SourceType.WEB for d in result.documents)
    mock_db_client.fetch_documents.assert_called_once_with(
        limit=10, offset=0, source_type=SourceType.WEB, extraction_state=None
    )


@pytest.mark.asyncio
async def test_list_documents_filter_by_extraction_state(mock_db_client, sample_documents):
    """Test filtering documents by extraction_state.

    RED phase: Will fail until implementation exists.
    """
    from packages.core.use_cases.list_documents import ListDocumentsUseCase

    pending_docs = [d for d in sample_documents if d.extraction_state == ExtractionState.PENDING]
    mock_db_client.fetch_documents = AsyncMock(return_value=pending_docs)
    mock_db_client.count_documents = AsyncMock(return_value=len(pending_docs))

    use_case = ListDocumentsUseCase(db_client=mock_db_client)
    result = await use_case.execute(
        limit=10, offset=0, extraction_state=ExtractionState.PENDING
    )

    assert result.total == 1
    assert len(result.documents) == 1
    assert result.documents[0].extraction_state == ExtractionState.PENDING
    mock_db_client.fetch_documents.assert_called_once_with(
        limit=10, offset=0, source_type=None, extraction_state=ExtractionState.PENDING
    )


@pytest.mark.asyncio
async def test_list_documents_combined_filters(mock_db_client, sample_documents):
    """Test filtering by both source_type and extraction_state.

    RED phase: Will fail until implementation exists.
    """
    from packages.core.use_cases.list_documents import ListDocumentsUseCase

    filtered = [
        d
        for d in sample_documents
        if d.source_type == SourceType.WEB and d.extraction_state == ExtractionState.COMPLETED
    ]
    mock_db_client.fetch_documents = AsyncMock(return_value=filtered)
    mock_db_client.count_documents = AsyncMock(return_value=len(filtered))

    use_case = ListDocumentsUseCase(db_client=mock_db_client)
    result = await use_case.execute(
        limit=10,
        offset=0,
        source_type=SourceType.WEB,
        extraction_state=ExtractionState.COMPLETED,
    )

    assert result.total == 1
    assert len(result.documents) == 1
    assert result.documents[0].source_type == SourceType.WEB
    assert result.documents[0].extraction_state == ExtractionState.COMPLETED


@pytest.mark.asyncio
async def test_list_documents_pagination(mock_db_client, sample_documents):
    """Test pagination with limit and offset.

    RED phase: Will fail until implementation exists.
    """
    from packages.core.use_cases.list_documents import ListDocumentsUseCase

    # Second page with 1 item
    mock_db_client.fetch_documents = AsyncMock(return_value=[sample_documents[2]])
    mock_db_client.count_documents = AsyncMock(return_value=3)

    use_case = ListDocumentsUseCase(db_client=mock_db_client)
    result = await use_case.execute(limit=2, offset=2)

    assert result.total == 3
    assert len(result.documents) == 1
    assert result.limit == 2
    assert result.offset == 2
    mock_db_client.fetch_documents.assert_called_once_with(
        limit=2, offset=2, source_type=None, extraction_state=None
    )


@pytest.mark.asyncio
async def test_list_documents_empty_result(mock_db_client):
    """Test listing when no documents match filters.

    RED phase: Will fail until implementation exists.
    """
    from packages.core.use_cases.list_documents import ListDocumentsUseCase

    mock_db_client.fetch_documents = AsyncMock(return_value=[])
    mock_db_client.count_documents = AsyncMock(return_value=0)

    use_case = ListDocumentsUseCase(db_client=mock_db_client)
    result = await use_case.execute(limit=10, offset=0, source_type=SourceType.GMAIL)

    assert result.total == 0
    assert len(result.documents) == 0
    assert result.limit == 10
    assert result.offset == 0
