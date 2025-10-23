"""End-to-end integration test for web ingestion pipeline (T055).

This test validates User Story 1 acceptance scenario:
- Full pipeline: WebReader → Normalizer → Chunker → Embedder → QdrantWriter
- Job state transitions: PENDING → RUNNING → COMPLETED
- Chunks stored in Qdrant with correct metadata
- Pipeline completes in <60s for 20-page docs

Markers:
- @pytest.mark.integration: Requires Docker services
- @pytest.mark.slow: End-to-end test takes longer to run
"""

import time
from uuid import uuid4

import pytest
from qdrant_client import QdrantClient

from packages.common.config import get_config
from packages.core.use_cases.ingest_web import IngestWebUseCase
from packages.ingest.chunker import Chunker
from packages.ingest.embedder import Embedder
from packages.ingest.normalizer import Normalizer
from packages.ingest.readers.web import WebReader
from packages.schemas.models import JobState
from packages.vector.writer import QdrantWriter


@pytest.mark.integration
@pytest.mark.slow
class TestIngestWebEndToEnd:
    """End-to-end integration tests for web ingestion pipeline."""

    @pytest.mark.asyncio
    async def test_web_ingestion_full_pipeline(
        self, docker_services_ready: None
    ) -> None:
        """Test complete web ingestion pipeline with real services.

        Acceptance Scenario (US1): Given Docker services are healthy, When the user
        ingests a web URL, Then the pipeline:
        1. Transitions job state: PENDING → RUNNING → COMPLETED
        2. Stores chunks in Qdrant with correct metadata
        3. Completes in <60s for 20-page docs
        4. Tracks job status with pages_processed and chunks_created

        This test requires:
        - taboot-crawler (Firecrawl) at http://taboot-crawler:3002
        - taboot-embed (TEI) at http://taboot-embed:80
        - taboot-vectors (Qdrant) at http://taboot-vectors:6333
        """
        # Setup: Load configuration
        config = get_config()

        # Use a simple, fast-loading test URL
        test_url = "https://example.com"
        collection_name = "taboot_documents"

        # Create all dependencies
        web_reader = WebReader(
            firecrawl_url=config.firecrawl_api_url,
            rate_limit_delay=0.1,  # Fast for testing
            max_retries=3,
        )
        normalizer = Normalizer()
        chunker = Chunker(chunk_size=512, chunk_overlap=51)
        embedder = Embedder(
            tei_url=config.tei_embedding_url,
            batch_size=32,
            expected_dim=1024,  # Qwen3-Embedding-0.6B uses 1024-dim
            timeout=30.0,
        )
        qdrant_writer = QdrantWriter(
            url=config.qdrant_url,
            collection_name=collection_name,
            batch_size=100,
        )

        try:
            # Initialize IngestWebUseCase
            use_case = IngestWebUseCase(
                web_reader=web_reader,
                normalizer=normalizer,
                chunker=chunker,
                embedder=embedder,
                qdrant_writer=qdrant_writer,
                collection_name=collection_name,
            )

            # Execute: Run ingestion pipeline
            start_time = time.time()
            job = use_case.execute(url=test_url, limit=1)
            end_time = time.time()
            elapsed = end_time - start_time

            # Verify: Job completed successfully
            assert job.state == JobState.COMPLETED, (
                f"Expected job state COMPLETED, got {job.state}. "
                f"Errors: {job.errors if job.errors else 'None'}"
            )

            # Verify: Job metadata is correct
            assert job.source_target == test_url
            assert job.pages_processed >= 1, "Should process at least 1 page"
            assert job.chunks_created >= 1, "Should create at least 1 chunk"

            # Verify: Job timestamps are set
            assert job.created_at is not None
            assert job.started_at is not None
            assert job.completed_at is not None
            assert job.started_at >= job.created_at
            assert job.completed_at >= job.started_at

            # Verify: Chunks are stored in Qdrant
            qdrant_client = QdrantClient(url=config.qdrant_url)
            try:
                # Scroll points to verify chunks exist
                scroll_result = qdrant_client.scroll(
                    collection_name=collection_name,
                    limit=100,
                    with_payload=True,
                    with_vectors=False,
                )

                points = scroll_result[0]
                assert len(points) >= 1, "Should have at least 1 point in Qdrant"

                # Verify point structure
                sample_point = points[0]
                assert sample_point.id is not None
                assert sample_point.payload is not None

                # Verify payload schema
                payload = sample_point.payload
                assert "doc_id" in payload
                assert "content" in payload
                assert "source_url" in payload
                assert "source_type" in payload
                assert payload["source_url"] == test_url
                assert payload["source_type"] == "web"

            finally:
                qdrant_client.close()

            # Verify: Performance target (<60s for 20-page docs)
            # For single-page test, expect much faster
            assert elapsed < 60.0, (
                f"Pipeline took {elapsed:.2f}s, expected <60s. "
                f"This was a single-page test, performance may vary for 20-page docs."
            )

            print(
                f"\n✓ Web ingestion E2E test passed:\n"
                f"  - Job: {job.job_id}\n"
                f"  - State: {job.state.value}\n"
                f"  - Pages: {job.pages_processed}\n"
                f"  - Chunks: {job.chunks_created}\n"
                f"  - Duration: {elapsed:.2f}s"
            )

        finally:
            # Cleanup: Close resources
            embedder.close()
            qdrant_writer.close()

    @pytest.mark.asyncio
    async def test_web_ingestion_error_handling(
        self, docker_services_ready: None
    ) -> None:
        """Test error handling in web ingestion pipeline.

        Acceptance Scenario: Given an invalid URL, When the pipeline executes,
        Then the job transitions to FAILED state with error details.
        """
        config = get_config()

        # Create dependencies with minimal setup
        web_reader = WebReader(
            firecrawl_url=config.firecrawl_api_url,
            rate_limit_delay=0.1,
            max_retries=1,  # Fail fast
        )
        normalizer = Normalizer()
        chunker = Chunker()
        embedder = Embedder(
            tei_url=config.tei_embedding_url,
            expected_dim=1024,
        )
        qdrant_writer = QdrantWriter(
            url=config.qdrant_url,
            collection_name="taboot_documents",
        )

        try:
            use_case = IngestWebUseCase(
                web_reader=web_reader,
                normalizer=normalizer,
                chunker=chunker,
                embedder=embedder,
                qdrant_writer=qdrant_writer,
                collection_name="taboot_documents",
            )

            # Execute with invalid URL (should fail)
            invalid_url = "https://this-domain-does-not-exist-12345.invalid"
            job = use_case.execute(url=invalid_url, limit=1)

            # Verify: Job failed
            assert job.state == JobState.FAILED, (
                f"Expected job state FAILED for invalid URL, got {job.state}"
            )

            # Verify: Error details are present
            assert job.errors is not None and len(job.errors) > 0, (
                "Expected error details in failed job"
            )

            # Verify: Job metadata
            assert job.source_target == invalid_url
            assert job.completed_at is not None

            print(
                f"\n✓ Error handling test passed:\n"
                f"  - Job: {job.job_id}\n"
                f"  - State: {job.state.value}\n"
                f"  - Error: {job.errors[0]['error'][:100]}..."
            )

        finally:
            embedder.close()
            qdrant_writer.close()

    @pytest.mark.asyncio
    async def test_web_ingestion_empty_result(
        self, docker_services_ready: None
    ) -> None:
        """Test handling of empty document result.

        Acceptance Scenario: Given a URL that returns no documents, When the
        pipeline executes, Then the job completes successfully with zero chunks.
        """
        config = get_config()

        # Create dependencies
        web_reader = WebReader(
            firecrawl_url=config.firecrawl_api_url,
            rate_limit_delay=0.1,
            max_retries=1,
        )
        normalizer = Normalizer()
        chunker = Chunker()
        embedder = Embedder(
            tei_url=config.tei_embedding_url,
            expected_dim=1024,
        )
        qdrant_writer = QdrantWriter(
            url=config.qdrant_url,
            collection_name="taboot_documents",
        )

        try:
            use_case = IngestWebUseCase(
                web_reader=web_reader,
                normalizer=normalizer,
                chunker=chunker,
                embedder=embedder,
                qdrant_writer=qdrant_writer,
                collection_name="taboot_documents",
            )

            # Execute with limit=0 (should return empty result)
            test_url = "https://example.com"
            job = use_case.execute(url=test_url, limit=0)

            # Verify: Job completed (empty result is not an error)
            assert job.state == JobState.COMPLETED, (
                f"Expected COMPLETED for empty result, got {job.state}"
            )

            # Verify: No pages or chunks processed
            assert job.pages_processed == 0
            assert job.chunks_created == 0

            print(
                f"\n✓ Empty result test passed:\n"
                f"  - Job: {job.job_id}\n"
                f"  - State: {job.state.value}\n"
                f"  - Pages: {job.pages_processed}\n"
                f"  - Chunks: {job.chunks_created}"
            )

        finally:
            embedder.close()
            qdrant_writer.close()


@pytest.mark.integration
@pytest.mark.slow
class TestWebIngestionPerformance:
    """Performance-focused tests for web ingestion pipeline."""

    @pytest.mark.asyncio
    async def test_multi_page_ingestion_performance(
        self, docker_services_ready: None
    ) -> None:
        """Test ingestion performance with multiple pages.

        Acceptance Scenario: Given a URL with multiple pages (up to 20), When the
        pipeline executes, Then it completes in <60s and maintains consistent
        throughput.
        """
        config = get_config()

        web_reader = WebReader(
            firecrawl_url=config.firecrawl_api_url,
            rate_limit_delay=0.1,
            max_retries=3,
        )
        normalizer = Normalizer()
        chunker = Chunker(chunk_size=512, chunk_overlap=51)
        embedder = Embedder(
            tei_url=config.tei_embedding_url,
            batch_size=32,
            expected_dim=1024,
            timeout=60.0,  # Longer timeout for multi-page
        )
        qdrant_writer = QdrantWriter(
            url=config.qdrant_url,
            collection_name="taboot_documents",
            batch_size=100,
        )

        try:
            use_case = IngestWebUseCase(
                web_reader=web_reader,
                normalizer=normalizer,
                chunker=chunker,
                embedder=embedder,
                qdrant_writer=qdrant_writer,
                collection_name="taboot_documents",
            )

            # Execute with multiple pages
            test_url = "https://example.com"
            page_limit = 5  # Conservative for CI/testing

            start_time = time.time()
            job = use_case.execute(url=test_url, limit=page_limit)
            end_time = time.time()
            elapsed = end_time - start_time

            # Verify: Job completed
            assert job.state == JobState.COMPLETED

            # Verify: Performance metrics
            pages_per_sec = job.pages_processed / elapsed if elapsed > 0 else 0
            chunks_per_sec = job.chunks_created / elapsed if elapsed > 0 else 0

            print(
                f"\n✓ Performance test passed:\n"
                f"  - Pages: {job.pages_processed}\n"
                f"  - Chunks: {job.chunks_created}\n"
                f"  - Duration: {elapsed:.2f}s\n"
                f"  - Throughput: {pages_per_sec:.2f} pages/sec, "
                f"{chunks_per_sec:.2f} chunks/sec"
            )

            # Verify: Throughput is reasonable
            assert elapsed < 60.0, (
                f"Multi-page ingestion took {elapsed:.2f}s, expected <60s"
            )

        finally:
            embedder.close()
            qdrant_writer.close()
