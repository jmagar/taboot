"""Background extraction worker (T170).

Polls Redis queue for pending extraction jobs and processes them asynchronously.
Supports graceful shutdown and error handling.
"""

import asyncio
import json
import logging
import signal
from types import FrameType
from typing import Protocol
from uuid import UUID

import psycopg2
from redis import asyncio as redis

from packages.clients.postgres_document_store import PostgresDocumentStore
from packages.common.config import get_config
from packages.core.use_cases.extract_pending import ExtractPendingUseCase
from packages.extraction.orchestrator import ExtractionOrchestrator
from packages.extraction.tier_a import parsers
from packages.extraction.tier_a.patterns import EntityPatternMatcher
from packages.extraction.tier_b.window_selector import WindowSelector
from packages.extraction.tier_c.llm_client import TierCLLMClient

logger = logging.getLogger(__name__)

# Queue names
QUEUE_EXTRACTION = "queue:extraction"


class SingleDocExtractor(Protocol):
    """Protocol for single-document extraction."""

    async def execute(self, doc_id: UUID) -> None:
        """Execute extraction for a single document.

        Args:
            doc_id: Document ID to extract.
        """
        ...


class SingleDocExtractorAdapter:
    """Adapter for ExtractPendingUseCase to SingleDocExtractor protocol.

    Wraps ExtractPendingUseCase and filters to process a single document by doc_id.
    This adapter allows the worker to process individual documents from the queue
    while reusing the batch-oriented ExtractPendingUseCase infrastructure.
    """

    def __init__(
        self,
        use_case: ExtractPendingUseCase,
        document_store: PostgresDocumentStore,
    ) -> None:
        """Initialize adapter with use case and document store.

        Args:
            use_case: ExtractPendingUseCase instance for extraction pipeline.
            document_store: PostgresDocumentStore for document filtering.
        """
        self.use_case = use_case
        self.document_store = document_store
        logger.info("Initialized SingleDocExtractorAdapter")

    async def execute(self, doc_id: UUID) -> None:
        """Execute extraction for a single document.

        Filters pending documents by doc_id and processes through the use case.
        If the document is not in PENDING state or doesn't exist, logs a warning.

        Args:
            doc_id: Document ID to extract.

        Raises:
            Exception: If extraction pipeline fails for the document.
        """
        # Query all pending documents (use case handles filtering by PENDING state)
        # Then filter by doc_id
        from packages.schemas.models import Document

        pending_docs = self.document_store.query_pending(limit=None)
        target_doc: Document | None = None

        for doc in pending_docs:
            if doc.doc_id == doc_id:
                target_doc = doc
                break

        if target_doc is None:
            logger.warning(
                f"Document {doc_id} not found in PENDING state - may have been "
                f"processed already or does not exist"
            )
            return

        # Process single document by temporarily replacing query_pending
        # to return only this document
        class SingleDocStore:
            """Wrapper that filters to single document."""

            def __init__(self, base_store: PostgresDocumentStore, doc: Document):
                self.base_store = base_store
                self.target_doc = doc

            def query_pending(self, limit: int | None = None) -> list[Document]:
                """Return only the target document."""
                return [self.target_doc]

            def get_content(self, doc_id: UUID) -> str:
                """Delegate to base store."""
                return self.base_store.get_content(doc_id)

            def update_document(self, document: Document) -> None:
                """Delegate to base store."""
                self.base_store.update_document(document)

        # Create single-doc filtered store
        single_doc_store = SingleDocStore(self.document_store, target_doc)

        # Execute use case with filtered store
        # Temporarily swap the store
        original_store = self.use_case.document_store
        self.use_case.document_store = single_doc_store

        try:
            result = await self.use_case.execute(limit=1)
            logger.info(
                f"Extraction complete for {doc_id}: processed={result['processed']}, "
                f"succeeded={result['succeeded']}, failed={result['failed']}"
            )
        finally:
            # Restore original store
            self.use_case.document_store = original_store


class ExtractionWorker:
    """Background worker for processing extraction jobs.

    Polls Redis extraction queue and processes documents through the
    multi-tier extraction pipeline (Tier A → B → C).
    """

    def __init__(
        self,
        redis_client: "redis.Redis[str]",
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
            result = await self.redis_client.blpop(QUEUE_EXTRACTION, timeout=self.poll_timeout)

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

                # Validate UUID format
                try:
                    uuid = UUID(doc_id)
                except ValueError:
                    logger.error("Invalid job data: bad doc_id format")
                    return

                logger.info("Processing extraction job for doc_id=%s", doc_id)

                # Process job if use case provided
                if self.extract_use_case:
                    await self.extract_use_case.execute(uuid)
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

    Sets up all dependencies (Redis, PostgreSQL, extraction pipeline)
    and runs the worker until stopped.
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info("Starting extraction worker initialization")

    # Load configuration
    config = get_config()

    # Create Redis client (decode to str for JSON parsing)
    logger.info(f"Connecting to Redis at {config.redis_url}")
    redis_client = redis.from_url(config.redis_url, decode_responses=True)

    # Create PostgreSQL connection
    logger.info(f"Connecting to PostgreSQL at {config.postgres_host}:{config.postgres_port}")
    pg_conn = psycopg2.connect(
        host=config.postgres_host,
        port=config.postgres_port,
        user=config.postgres_user,
        password=config.postgres_password.get_secret_value(),
        dbname=config.postgres_db,
    )

    # Initialize document store
    document_store = PostgresDocumentStore(conn=pg_conn)

    # Initialize Tier A components
    logger.info("Initializing Tier A extraction components")
    tier_a_patterns = EntityPatternMatcher()

    # Initialize Tier B window selector
    logger.info("Initializing Tier B window selector")
    window_selector = WindowSelector()

    # Initialize Tier C LLM client
    logger.info("Initializing Tier C LLM client (qwen3:4b)")
    llm_client = TierCLLMClient(
        model="qwen3:4b",
        redis_client=redis_client,
        batch_size=config.tier_c_batch_size,
        temperature=0.0,
    )

    # Initialize ExtractionOrchestrator
    logger.info("Initializing ExtractionOrchestrator")
    orchestrator = ExtractionOrchestrator(
        tier_a_parser=parsers,  # Module with parse_code_blocks, parse_tables functions
        tier_a_patterns=tier_a_patterns,
        window_selector=window_selector,
        llm_client=llm_client,
        redis_client=redis_client,
    )

    # Initialize ExtractPendingUseCase
    logger.info("Initializing ExtractPendingUseCase")
    extract_use_case = ExtractPendingUseCase(
        orchestrator=orchestrator,
        document_store=document_store,
    )

    # Wrap use case in SingleDocExtractor adapter
    logger.info("Wrapping use case in SingleDocExtractorAdapter")
    single_doc_extractor = SingleDocExtractorAdapter(
        use_case=extract_use_case,
        document_store=document_store,
    )

    # Create worker
    logger.info("Creating ExtractionWorker")
    worker = ExtractionWorker(
        redis_client=redis_client,
        extract_use_case=single_doc_extractor,
    )

    # Setup signal handlers for graceful shutdown
    def handle_signal(sig: int, _frame: FrameType | None) -> None:
        logger.info("Received signal %s", sig)
        worker.signal_stop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Run worker
    logger.info("Starting extraction worker loop")
    try:
        await worker.run()
    finally:
        logger.info("Cleaning up resources")
        await redis_client.close()
        document_store.close()


if __name__ == "__main__":
    asyncio.run(main())
