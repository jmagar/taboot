"""Background extraction worker (T170).

Polls Redis queue for pending extraction jobs and processes them asynchronously.
Supports graceful shutdown and error handling.
"""

import asyncio
import json
import logging
import os
import signal
from types import FrameType
from typing import Protocol
from uuid import UUID

from redis import asyncio as redis

logger = logging.getLogger(__name__)


class SingleDocExtractor(Protocol):
    """Protocol for single-document extraction."""

    async def execute(self, doc_id: UUID) -> None:
        """Execute extraction for a single document.

        Args:
            doc_id: Document ID to extract.
        """
        ...


class ExtractionWorker:
    """Background worker for processing extraction jobs.

    Polls Redis extraction queue and processes documents through the
    multi-tier extraction pipeline (Tier A → B → C).
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        extract_use_case: SingleDocExtractor | None = None,
        poll_timeout: int = 5,
    ) -> None:
        """Initialize ExtractionWorker.

        Args:
            redis_client: Redis client for queue operations.
            extract_use_case: Use case for extraction (optional for testing).
            poll_timeout: Timeout for Redis BLPOP in seconds.
        """
        self.redis_client = redis_client
        self.extract_use_case = extract_use_case
        self.poll_timeout = poll_timeout
        self._stop_flag = False

        logger.info("Initialized ExtractionWorker (poll_timeout=%ss)", poll_timeout)

    def should_stop(self) -> bool:
        """Check if worker should stop.

        Returns:
            True if worker should stop, False otherwise.
        """
        return self._stop_flag

    def signal_stop(self) -> None:
        """Signal worker to stop gracefully."""
        logger.info("Received stop signal")
        self._stop_flag = True

    async def poll_once(self) -> None:
        """Poll queue once and process a single job if available.

        Returns:
            None

        Raises:
            Does not raise - handles errors internally.
        """
        try:
            # Poll queue with timeout
            result = await self.redis_client.blpop(
                "queue:extraction", timeout=self.poll_timeout
            )

            if not result:
                # No job available
                return

            _queue_name, job_data = result

            # Parse job
            try:
                job = json.loads(job_data)
                doc_id = job.get("doc_id")

                if not doc_id:
                    logger.error("Invalid job data: missing doc_id")
                    return

                logger.info("Processing extraction job for doc_id=%s", doc_id)

                # Process job if use case provided
                if self.extract_use_case:
                    await self.extract_use_case.execute(UUID(doc_id))
                    logger.info("Completed extraction for doc_id=%s", doc_id)

            except json.JSONDecodeError:
                logger.exception("Failed to parse job data")
            except Exception:
                logger.exception("Extraction failed for job")
                # Job fails but worker continues

        except Exception:
            logger.exception("Error in poll_once")

    async def run(self) -> None:
        """Run worker continuously until stopped.

        Polls queue and processes jobs in a loop. Handles graceful shutdown.
        """
        logger.info("Starting extraction worker loop")

        try:
            while not self.should_stop():
                await self.poll_once()

        except asyncio.CancelledError:
            logger.info("Worker cancelled")
        except Exception:
            logger.exception("Worker error")
        finally:
            logger.info("Worker stopped")


async def main() -> None:
    """Main entry point for extraction worker.

    Sets up Redis connection, initializes worker, and runs until stopped.
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Get Redis URL from environment
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    # Create Redis client (decode to str for JSON parsing)
    redis_client = redis.from_url(redis_url, decode_responses=True)

    # Create worker
    # TODO: Wire a SingleDocExtractor use case here when available
    worker = ExtractionWorker(
        redis_client=redis_client,
        extract_use_case=None,
    )

    # Setup signal handlers for graceful shutdown
    def handle_signal(sig: int, _frame: FrameType | None) -> None:
        logger.info("Received signal %s", sig)
        worker.signal_stop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Run worker
    try:
        await worker.run()
    finally:
        await redis_client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
