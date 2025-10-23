"""Tests for extraction orchestrator coordinating Tier A → B → C execution."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from packages.extraction.orchestrator import ExtractionOrchestrator
from packages.extraction.tier_c.schema import ExtractionResult, Triple
from packages.schemas.models import ExtractionJob, ExtractionState


@pytest.fixture
def mock_tier_a_parser():
    """Mock Tier A parser."""
    parser = Mock()
    parser.parse_code_blocks = Mock(return_value=[])
    parser.parse_tables = Mock(return_value=[])
    return parser


@pytest.fixture
def mock_tier_a_patterns():
    """Mock Tier A pattern matcher."""
    patterns = Mock()
    patterns.find_matches = Mock(return_value=[
        {
            "entity_type": "service",
            "text": "postgres",
            "start": 0,
            "end": 8,
        }
    ])
    return patterns


@pytest.fixture
def mock_window_selector():
    """Mock Tier B window selector."""
    selector = Mock()
    selector.select_windows = Mock(return_value=[
        {
            "content": "Test window content",
            "token_count": 4,
            "start": 0,
            "end": 19,
        }
    ])
    return selector


@pytest.fixture
def mock_llm_client():
    """Mock Tier C LLM client."""
    client = AsyncMock()
    # Return extraction result with one triple
    result = ExtractionResult(
        triples=[
            Triple(
                subject="api-service",
                predicate="DEPENDS_ON",
                object="postgres",
                confidence=0.9,
            )
        ]
    )
    client.batch_extract = AsyncMock(return_value=[result])
    return client


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for state management."""
    redis = AsyncMock()
    redis.set = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.incr = AsyncMock()
    return redis


@pytest.fixture
def orchestrator(
    mock_tier_a_parser,
    mock_tier_a_patterns,
    mock_window_selector,
    mock_llm_client,
    mock_redis_client,
):
    """Create ExtractionOrchestrator with mocked dependencies."""
    return ExtractionOrchestrator(
        tier_a_parser=mock_tier_a_parser,
        tier_a_patterns=mock_tier_a_patterns,
        window_selector=mock_window_selector,
        llm_client=mock_llm_client,
        redis_client=mock_redis_client,
    )


@pytest.mark.asyncio
async def test_orchestrator_coordinates_tier_execution(orchestrator, mock_redis_client):
    """Test that orchestrator coordinates Tier A → B → C execution."""
    doc_id = uuid4()
    content = "api-service depends on postgres for data storage"

    job = await orchestrator.process_document(doc_id, content)

    # Verify job returned
    assert isinstance(job, ExtractionJob)
    assert job.doc_id == doc_id
    assert job.state == ExtractionState.COMPLETED

    # Verify metrics tracked
    assert job.tier_a_triples >= 0  # At least tracked
    assert job.tier_b_windows >= 0
    assert job.tier_c_triples >= 0

    # Verify state transitions happened (check Redis calls)
    assert mock_redis_client.set.call_count >= 4  # pending → tier_a → tier_b → tier_c → completed


@pytest.mark.asyncio
async def test_orchestrator_state_transitions(orchestrator, mock_redis_client):
    """Test state transitions tracked in Redis.

    States: pending → tier_a_done → tier_b_done → tier_c_done → completed
    """
    doc_id = uuid4()
    content = "Test content"

    job = await orchestrator.process_document(doc_id, content)

    # Verify final state
    assert job.state == ExtractionState.COMPLETED

    # Verify Redis state updates were made
    # Each tier transition should call _update_state which calls redis.set
    state_updates = [
        call for call in mock_redis_client.set.call_args_list
        if "state" in str(call) or "extraction_job" in str(call)
    ]
    assert len(state_updates) >= 4


@pytest.mark.asyncio
async def test_orchestrator_tracks_metrics(
    orchestrator,
    mock_tier_a_patterns,
    mock_window_selector,
    mock_llm_client,
):
    """Test metrics tracked (tier_a_triples, tier_b_windows, tier_c_triples)."""
    doc_id = uuid4()
    content = "Test content with postgres service"

    # Configure mocks to return specific counts
    mock_tier_a_patterns.find_matches.return_value = [
        {"entity_type": "service", "text": "postgres", "start": 0, "end": 8}
    ]
    mock_window_selector.select_windows.return_value = [
        {"content": "window1", "token_count": 3, "start": 0, "end": 7},
        {"content": "window2", "token_count": 3, "start": 8, "end": 15},
    ]
    mock_llm_client.batch_extract.return_value = [
        ExtractionResult(
            triples=[
                Triple(subject="s1", predicate="p1", object="o1", confidence=0.9)
            ]
        ),
        ExtractionResult(
            triples=[
                Triple(subject="s2", predicate="p2", object="o2", confidence=0.8),
                Triple(subject="s3", predicate="p3", object="o3", confidence=0.7),
            ]
        ),
    ]

    job = await orchestrator.process_document(doc_id, content)

    # Verify metrics
    assert job.tier_a_triples == 1  # 1 pattern match
    assert job.tier_b_windows == 2  # 2 windows selected
    assert job.tier_c_triples == 3  # 1 + 2 triples from LLM


@pytest.mark.asyncio
async def test_orchestrator_error_handling_with_retry(
    orchestrator, mock_llm_client, mock_redis_client
):
    """Test error handling with retry logic (max 3 retries)."""
    doc_id = uuid4()
    content = "Test content"

    # Make Tier C fail twice, then succeed
    mock_llm_client.batch_extract.side_effect = [
        Exception("LLM error 1"),
        Exception("LLM error 2"),
        [ExtractionResult(triples=[])],  # Success on third try
    ]

    job = await orchestrator.process_document(doc_id, content)

    # Should succeed after retries
    assert job.state == ExtractionState.COMPLETED
    assert job.retry_count == 2  # Two retries before success


@pytest.mark.asyncio
async def test_orchestrator_fails_after_max_retries(orchestrator, mock_llm_client):
    """Test transition to FAILED state after max retries."""
    doc_id = uuid4()
    content = "Test content"

    # Make Tier C always fail
    mock_llm_client.batch_extract.side_effect = Exception("Persistent LLM error")

    job = await orchestrator.process_document(doc_id, content)

    # Should fail after 3 retries
    assert job.state == ExtractionState.FAILED
    assert job.retry_count == 3
    assert job.errors is not None
    assert "Persistent LLM error" in str(job.errors)
