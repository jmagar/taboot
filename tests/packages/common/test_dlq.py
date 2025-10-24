"""Tests for Dead Letter Queue (T171).

Tests Redis-based DLQ with retry policy and exponential backoff.
Follows TDD RED-GREEN-REFACTOR methodology.
"""

from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def mock_redis_client() -> None:
    """Mock Redis client for DLQ operations."""
    client = AsyncMock()
    client.lpush = AsyncMock(return_value=1)
    client.hset = AsyncMock(return_value=1)
    client.hget = AsyncMock(return_value=None)
    client.hincrby = AsyncMock(return_value=1)
    return client


@pytest.mark.asyncio
async def test_dlq_sends_failed_job_to_queue(mock_redis_client) -> None:
    """Test DLQ sends failed job to dead letter queue.

    RED phase: Will fail until DLQ exists.
    """
    from packages.common.dlq import DeadLetterQueue

    dlq = DeadLetterQueue(redis_client=mock_redis_client)

    job_data = {"doc_id": "test-123", "attempt": 1}
    error = "Extraction failed"

    await dlq.send_to_dlq(job_data=job_data, error=error)

    # Should have pushed to DLQ
    mock_redis_client.lpush.assert_called_once()


@pytest.mark.asyncio
async def test_dlq_tracks_retry_count(mock_redis_client) -> None:
    """Test DLQ tracks retry count for jobs.

    RED phase: Will fail until DLQ exists.
    """
    from packages.common.dlq import DeadLetterQueue

    dlq = DeadLetterQueue(redis_client=mock_redis_client)

    job_id = "job-123"

    # First retry
    count = await dlq.increment_retry_count(job_id)
    assert count == 1

    # Second retry
    mock_redis_client.hincrby = AsyncMock(return_value=2)
    count = await dlq.increment_retry_count(job_id)
    assert count == 2


@pytest.mark.asyncio
async def test_dlq_respects_max_retries(mock_redis_client) -> None:
    """Test DLQ respects max retry limit.

    RED phase: Will fail until DLQ exists.
    """
    from packages.common.dlq import DeadLetterQueue

    dlq = DeadLetterQueue(redis_client=mock_redis_client, max_retries=3)

    # Simulate job with 3 retries
    mock_redis_client.hget = AsyncMock(return_value=b"3")

    should_retry = await dlq.should_retry(job_id="job-123")

    assert should_retry is False


@pytest.mark.asyncio
async def test_dlq_allows_retry_below_max(mock_redis_client) -> None:
    """Test DLQ allows retry when below max.

    RED phase: Will fail until DLQ exists.
    """
    from packages.common.dlq import DeadLetterQueue

    dlq = DeadLetterQueue(redis_client=mock_redis_client, max_retries=3)

    # Simulate job with 2 retries
    mock_redis_client.hget = AsyncMock(return_value=b"2")

    should_retry = await dlq.should_retry(job_id="job-123")

    assert should_retry is True


@pytest.mark.asyncio
async def test_dlq_calculates_backoff_delay(mock_redis_client) -> None:
    """Test DLQ calculates exponential backoff delay.

    RED phase: Will fail until DLQ exists.
    """
    from packages.common.dlq import DeadLetterQueue

    dlq = DeadLetterQueue(redis_client=mock_redis_client, base_delay_seconds=2)

    # Retry 1: 2 seconds
    delay1 = dlq.calculate_backoff_delay(retry_count=1)
    assert delay1 == 2

    # Retry 2: 4 seconds (2 ^ 2)
    delay2 = dlq.calculate_backoff_delay(retry_count=2)
    assert delay2 == 4

    # Retry 3: 8 seconds (2 ^ 3)
    delay3 = dlq.calculate_backoff_delay(retry_count=3)
    assert delay3 == 8


@pytest.mark.asyncio
async def test_dlq_stores_error_metadata(mock_redis_client) -> None:
    """Test DLQ stores error metadata with job.

    RED phase: Will fail until DLQ exists.
    """
    from packages.common.dlq import DeadLetterQueue

    dlq = DeadLetterQueue(redis_client=mock_redis_client)

    job_data = {"doc_id": "test-123"}
    error = "Connection timeout"

    await dlq.send_to_dlq(job_data=job_data, error=error)

    # Should store error metadata
    assert mock_redis_client.lpush.called
    call_args = mock_redis_client.lpush.call_args
    assert "error" in str(call_args) or error in str(call_args)
