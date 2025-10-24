"""Dead Letter Queue (DLQ) implementation with retry policy (T172).

Redis-based DLQ with exponential backoff retry mechanism.
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from redis import asyncio as redis

logger = logging.getLogger(__name__)


class DeadLetterQueue:
    """Redis-based Dead Letter Queue with retry policy.

    Features:
    - Tracks retry count per job
    - Exponential backoff calculation
    - Max retry limit (default: 3)
    - Error metadata storage
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        max_retries: int = 3,
        base_delay_seconds: int = 2,
    ) -> None:
        """Initialize DeadLetterQueue.

        Args:
            redis_client: Redis client for queue operations.
            max_retries: Maximum retry attempts (default: 3).
            base_delay_seconds: Base delay for exponential backoff (default: 2).
        """
        self.redis_client = redis_client
        self.max_retries = max_retries
        self.base_delay_seconds = base_delay_seconds

        logger.info(
            "Initialized DeadLetterQueue",
            extra={
                "max_retries": max_retries,
                "base_delay_seconds": base_delay_seconds,
            },
        )

    async def send_to_dlq(
        self,
        job_data: dict[str, Any],
        error: str,
        queue_name: str = "queue:dlq",
    ) -> None:
        """Send failed job to dead letter queue with error metadata.

        Args:
            job_data: Original job data.
            error: Error message describing failure.
            queue_name: DLQ queue name (default: queue:dlq).
        """
        # Add error metadata
        dlq_entry = {
            **job_data,
            "error": error,
            "failed_at": datetime.now(UTC).isoformat(),
        }

        # Convert to JSON
        entry_json = json.dumps(dlq_entry)

        # Push to DLQ
        await self.redis_client.lpush(queue_name, entry_json)

        logger.warning(
            "Sent job to DLQ",
            extra={"doc_id": job_data.get("doc_id", "unknown"), "error": error},
        )

    async def increment_retry_count(self, job_id: str) -> int:
        """Increment retry count for a job.

        Args:
            job_id: Unique job identifier.

        Returns:
            Current retry count after increment.
        """
        count = await self.redis_client.hincrby("retry_counts", job_id, 1)

        logger.debug(
            "Incremented retry count", extra={"job_id": job_id, "count": count}
        )

        return count

    async def get_retry_count(self, job_id: str) -> int:
        """Get current retry count for a job.

        Args:
            job_id: Unique job identifier.

        Returns:
            Current retry count (0 if not found).
        """
        count_bytes = await self.redis_client.hget("retry_counts", job_id)

        if count_bytes is None:
            return 0

        return int(count_bytes)

    async def should_retry(self, job_id: str) -> bool:
        """Check if job should be retried based on retry count.

        Args:
            job_id: Unique job identifier.

        Returns:
            True if retry count < max_retries, False otherwise.
        """
        current_count = await self.get_retry_count(job_id)

        should_retry = current_count < self.max_retries

        logger.debug(
            "Retry check",
            extra={
                "job_id": job_id,
                "count": current_count,
                "max": self.max_retries,
                "should_retry": should_retry,
            },
        )

        return should_retry

    def calculate_backoff_delay(self, retry_count: int) -> int:
        """Calculate exponential backoff delay for retry.

        Formula: base_delay * (2 ^ (retry_count - 1))
        Example with base_delay=2:
        - Retry 1: 2 seconds (2 * 2^0)
        - Retry 2: 4 seconds (2 * 2^1)
        - Retry 3: 8 seconds (2 * 2^2)

        Args:
            retry_count: Current retry attempt number (1-indexed).

        Returns:
            Delay in seconds before next retry.
        """
        delay = self.base_delay_seconds * (2 ** (retry_count - 1))

        logger.debug(
            "Calculated backoff delay",
            extra={"retry_count": retry_count, "delay_s": delay},
        )

        return delay

    async def clear_retry_count(self, job_id: str) -> None:
        """Clear retry count for a successful job.

        Args:
            job_id: Unique job identifier.
        """
        await self.redis_client.hdel("retry_counts", job_id)

        logger.debug("Cleared retry count", extra={"job_id": job_id})


# Export public API
__all__ = ["DeadLetterQueue"]
