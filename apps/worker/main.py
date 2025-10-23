"""Background extraction worker (T170).

Polls Redis queue for pending extraction jobs and processes them asynchronously.
Supports graceful shutdown and error handling.
"""

import asyncio
import json
import logging
import os
import signal
from typing import Any, Callable, Optional

from redis import asyncio as redis

logger = logging.getLogger(__name__)


class ExtractionWorker:
    """Background worker for processing extraction jobs.

    Polls Redis extraction queue and processes documents through the
    multi-tier extraction pipeline (Tier A → B → C).
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        extract_use_case: Optional[Any] = None,
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

        logger.info(f"Initialized ExtractionWorker (poll_timeout={poll_timeout}s)")

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

            queue_name, job_data = result

            # Parse job
            try:
                job = json.loads(job_data)
                doc_id = job.get("doc_id")

                if not doc_id:
                    logger.error(f"Invalid job data: {job_data}")
                    return

                logger.info(f"Processing extraction job for doc_id={doc_id}")

                # Process job if use case provided
                if self.extract_use_case:
                    await self.extract_use_case.execute(doc_id=doc_id)
                    logger.info(f"Completed extraction for doc_id={doc_id}")

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse job data: {e}", exc_info=True)
            except Exception as e:
                logger.error(
                    f"Extraction failed for job: {e}", exc_info=True
                )
                # Job fails but worker continues

        except Exception as e:
            logger.error(f"Error in poll_once: {e}", exc_info=True)

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
        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
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

    # Create Redis client
    redis_client = redis.from_url(redis_url, decode_responses=False)

    # Import extraction use case
    from packages.core.use_cases.extract_pending import ExtractPendingUseCase

    # Create use case (simplified - real implementation would need dependencies)
    extract_use_case = None  # TODO: Initialize with real dependencies

    # Create worker
    worker = ExtractionWorker(
        redis_client=redis_client,
        extract_use_case=extract_use_case,
    )

    # Setup signal handlers for graceful shutdown
    def handle_signal(sig: int, frame: Any) -> None:
        logger.info(f"Received signal {sig}")
        worker.signal_stop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Run worker
    try:
        await worker.run()
    finally:
        await redis_client.close()


if __name__ == "__main__":
    asyncio.run(main())
