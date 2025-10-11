"""Job management layer orchestrating Firecrawl ingestion runs."""

from __future__ import annotations

import asyncio
import uuid
from contextlib import suppress
from datetime import UTC, datetime
from typing import Any

from llamacrawl.api.job_store import FirecrawlJobStore
from llamacrawl.api.models import (
    FirecrawlJobCreateRequest,
    FirecrawlJobProgress,
    FirecrawlJobRecord,
    FirecrawlJobStatus,
    FirecrawlJobSummary,
)
from llamacrawl.config import Config
from llamacrawl.embeddings.tei import TEIEmbedding
from llamacrawl.ingestion.pipeline import IngestionPipeline
from llamacrawl.models.document import Document
from llamacrawl.readers.firecrawl import FirecrawlReader
from llamacrawl.storage.neo4j import Neo4jClient
from llamacrawl.storage.qdrant import QdrantClient
from llamacrawl.storage.redis import RedisClient
from llamacrawl.utils.logging import get_logger

logger = get_logger(__name__)


class FirecrawlJobManager:
    """Coordinates submission and execution of Firecrawl ingestion jobs."""

    def __init__(
        self,
        config: Config,
        redis_client: RedisClient,
        job_store: FirecrawlJobStore,
        qdrant_client: QdrantClient,
        neo4j_client: Neo4jClient,
        embed_model: TEIEmbedding,
    ) -> None:
        self._config = config
        self._redis_client = redis_client
        self._job_store = job_store
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._task_lock = asyncio.Lock()

        # Heavy clients are passed in from app.py for sharing between managers
        self._neo4j_client = neo4j_client
        self._qdrant_client = qdrant_client
        self._embed_model = embed_model

    async def submit_job(self, request: FirecrawlJobCreateRequest) -> FirecrawlJobRecord:
        """Create a new Firecrawl job and start background processing."""
        job_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        record = FirecrawlJobRecord(
            job_id=job_id,
            url=request.url,
            mode=request.mode,
            status=FirecrawlJobStatus.QUEUED,
            created_at=now,
            updated_at=now,
            progress=FirecrawlJobProgress(),
            request_payload=request.model_dump(),
        )
        self._job_store.upsert(record)

        async with self._task_lock:
            task = asyncio.create_task(self._execute_job(record, request))
            task.add_done_callback(lambda _: self._tasks.pop(job_id, None))
            self._tasks[job_id] = task

        return record

    async def _execute_job(
        self,
        record: FirecrawlJobRecord,
        request: FirecrawlJobCreateRequest,
    ) -> None:
        """Run the Firecrawl ingestion workflow asynchronously."""
        job_id = record.job_id
        self._job_store.update_status(
            job_id,
            FirecrawlJobStatus.RUNNING,
            started_at=datetime.now(UTC),
        )

        reader_config = self._build_reader_config(request)
        reader = FirecrawlReader(
            source_name=f"firecrawl_{request.mode.value}",
            config=reader_config,
            redis_client=self._redis_client,
        )

        def progress_callback(completed: int, total: int | None, status: str) -> None:
            self._job_store.update_progress(
                job_id,
                completed=completed,
                total=total,
                status=status,
            )

        url_str = str(request.url)

        try:
            documents = await reader.aload_data(
                url=url_str,
                mode=request.mode.value,  # type: ignore[arg-type]
                limit=request.limit,
                max_depth=request.max_depth,
                formats=request.formats,
                prompt=request.prompt,
                schema=request.schema,
                progress_callback=progress_callback,
                include_paths=request.include_paths,
                exclude_paths=request.exclude_paths,
            )
        except Exception as exc:
            logger.exception("Firecrawl crawl failed", extra={"job_id": job_id})
            self._job_store.update_status(
                job_id,
                FirecrawlJobStatus.FAILED,
                error=str(exc),
                completed_at=datetime.now(UTC),
            )
            return

        if not documents:
            logger.warning("Firecrawl crawl returned no documents", extra={"job_id": job_id})
            self._job_store.update_status(
                job_id,
                FirecrawlJobStatus.COMPLETED,
                completed_at=datetime.now(UTC),
                summary=FirecrawlJobSummary(
                    total=0,
                    processed=0,
                    deduplicated=0,
                    failed=0,
                    duration_seconds=0.0,
                ),
            )
            return

        self._job_store.update_progress(
            job_id,
            completed=len(documents),
            total=len(documents),
            status="ingesting",
        )

        try:
            documents_ingested = await asyncio.to_thread(
                self._ingest_documents,
                request,
                documents,
            )
        except Exception as exc:
            logger.exception("Ingestion pipeline failed", extra={"job_id": job_id})
            self._job_store.update_status(
                job_id,
                FirecrawlJobStatus.FAILED,
                error=str(exc),
                completed_at=datetime.now(UTC),
            )
            return

        summary = FirecrawlJobSummary(**documents_ingested)
        self._job_store.update_status(
            job_id,
            FirecrawlJobStatus.COMPLETED,
            completed_at=datetime.now(UTC),
            summary=summary,
        )

    def _ingest_documents(
        self,
        request: FirecrawlJobCreateRequest,
        documents: list[Document],
    ) -> dict[str, Any]:
        """Run the ingestion pipeline in a thread to avoid blocking the event loop."""
        pipeline = IngestionPipeline(
            config=self._config,
            redis_client=self._redis_client,
            qdrant_client=self._qdrant_client,
            neo4j_client=self._neo4j_client,
            embed_model=self._embed_model,
        )
        summary = pipeline.ingest_documents(
            source=f"firecrawl_{request.mode.value}",
            documents=documents,
        )
        return summary.to_dict()

    def _build_reader_config(self, request: FirecrawlJobCreateRequest) -> dict[str, Any]:
        """Merge request overrides with default Firecrawl source configuration."""
        cfg = self._config.sources.firecrawl
        location = None
        if request.location_country:
            location = {
                "country": request.location_country.upper(),
                "languages": request.location_languages
                or [f"en-{request.location_country.upper()}"]
            }
        elif cfg.location:
            location = cfg.location.model_dump()

        reader_config: dict[str, Any] = {
            "max_pages": request.limit or cfg.max_pages,
            "default_crawl_depth": request.max_depth or cfg.default_crawl_depth,
            "formats": request.formats or cfg.formats,
            "include_paths": request.include_paths or cfg.include_paths,
            "exclude_paths": request.exclude_paths or cfg.exclude_paths,
            "location": location,
            "filter_non_english_metadata": (
                request.filter_non_english_metadata
                if request.filter_non_english_metadata is not None
                else cfg.filter_non_english_metadata
            ),
            "cache_max_age_ms": cfg.cache_max_age_ms,
            "max_concurrency": cfg.max_concurrency,
            "max_retries": cfg.max_retries,
            "retry_delay_ms": cfg.retry_delay_ms,
            "crawl_delay_ms": cfg.crawl_delay_ms,
            "timeout_ms": cfg.timeout_ms,
        }

        return reader_config

    async def shutdown(self) -> None:
        """Attempt to gracefully cancel any pending background jobs."""
        async with self._task_lock:
            tasks = list(self._tasks.values())
            self._tasks.clear()

        for task in tasks:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
