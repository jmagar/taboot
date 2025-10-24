"""Tests for extraction worker (T169).

Tests background worker that polls Redis queue and processes extraction jobs.
Follows TDD RED-GREEN-REFACTOR methodology.
"""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def mock_redis_client() -> None:
    """Mock Redis client for queue operations."""
    client = AsyncMock()
    return client


@pytest.fixture
def mock_extract_use_case() -> None:
    """Mock extraction use case."""
    use_case = AsyncMock()
    return use_case


@pytest.mark.asyncio
async def test_worker_polls_extraction_queue(mock_redis_client) -> None:
    """Test worker polls Redis extraction queue.

    RED phase: Will fail until worker exists.
    """
    from apps.worker.main import ExtractionWorker

    mock_redis_client.blpop = AsyncMock(return_value=None)  # Empty queue

    worker = ExtractionWorker(redis_client=mock_redis_client)

    # Poll once
    await worker.poll_once()

    mock_redis_client.blpop.assert_called_once()


@pytest.mark.asyncio
async def test_worker_processes_extraction_job(mock_redis_client, mock_extract_use_case) -> None:
    """Test worker processes extraction job from queue.

    RED phase: Will fail until worker exists.
    """
    from apps.worker.main import ExtractionWorker

    # Queue has one job
    job_data = b'{"doc_id": "test-doc-123"}'
    mock_redis_client.blpop = AsyncMock(return_value=("queue:extraction", job_data))

    worker = ExtractionWorker(
        redis_client=mock_redis_client,
        extract_use_case=mock_extract_use_case,
    )

    # Poll and process
    await worker.poll_once()

    # Should have processed the job
    mock_extract_use_case.execute.assert_called_once()


@pytest.mark.asyncio
async def test_worker_handles_processing_error(mock_redis_client, mock_extract_use_case) -> None:
    """Test worker handles extraction errors gracefully.

    RED phase: Will fail until worker exists.
    """
    from apps.worker.main import ExtractionWorker

    job_data = b'{"doc_id": "test-doc-123"}'
    mock_redis_client.blpop = AsyncMock(return_value=("queue:extraction", job_data))

    # Simulate extraction failure
    mock_extract_use_case.execute = AsyncMock(side_effect=ValueError("Extraction failed"))

    worker = ExtractionWorker(
        redis_client=mock_redis_client,
        extract_use_case=mock_extract_use_case,
    )

    # Should not raise, should handle error
    await worker.poll_once()

    # Job should have been attempted
    mock_extract_use_case.execute.assert_called_once()


@pytest.mark.asyncio
async def test_worker_runs_continuous_loop(mock_redis_client) -> None:
    """Test worker runs continuous polling loop.

    RED phase: Will fail until worker exists.
    """
    from apps.worker.main import ExtractionWorker

    # Return None after 2 polls to stop loop
    poll_count = 0

    async def mock_blpop(*args, **kwargs) -> None:
        nonlocal poll_count
        poll_count += 1
        if poll_count >= 2:
            # Signal to stop
            return None
        return None

    mock_redis_client.blpop = mock_blpop

    worker = ExtractionWorker(redis_client=mock_redis_client)

    # Run for 2 iterations
    with patch.object(worker, "should_stop", side_effect=[False, False, True]):
        await worker.run()

    assert poll_count >= 2


@pytest.mark.asyncio
async def test_worker_respects_shutdown_signal(mock_redis_client) -> None:
    """Test worker stops on shutdown signal.

    RED phase: Will fail until worker exists.
    """
    from apps.worker.main import ExtractionWorker

    worker = ExtractionWorker(redis_client=mock_redis_client)

    # Shutdown immediately
    worker.should_stop = lambda: True

    # Should return immediately without polling
    await worker.run()
