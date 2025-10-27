"""Ingestion endpoints for web crawling and document ingestion.

Provides POST /ingest and GET /ingest/{job_id} endpoints for creating and
monitoring ingestion jobs.

Required by FR-033: API MUST provide ingestion endpoints with job tracking.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from types import ModuleType

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from packages.ingest.postgres_job_store import PostgresJobStore

from datetime import UTC, datetime

from apps.api.deps.auth import verify_api_key
from packages.common.validators import URLValidationError, validate_url
from packages.core.use_cases.ingest_web import IngestWebUseCase
from packages.ingest.chunker import Chunker
from packages.ingest.embedder import Embedder
from packages.ingest.normalizer import Normalizer
from packages.ingest.readers.web import WebReader
from packages.schemas.models import (
    Document as DocumentModel,
)
from packages.schemas.models import (
    IngestionJob,
    JobState,
    SourceType,
)
from packages.vector.writer import QdrantWriter

redis_async: ModuleType | None
try:
    from redis import asyncio as redis_async
except ModuleNotFoundError:  # pragma: no cover - redis optional in some test suites
    redis_async = None

from packages.ingest.adapters.redis_streams_publisher import RedisDocumentEventPublisher
from packages.ingest.services.document_events import DocumentEventDispatcher

logger = logging.getLogger(__name__)

router = APIRouter()


@lru_cache(maxsize=1)
def _get_event_dispatcher() -> DocumentEventDispatcher | None:
    """Lazily construct a document event dispatcher when enabled."""

    if redis_async is None:
        return None

    from packages.common.config import get_config

    config = get_config()

    if not config.enable_ingest_events:
        return None

    redis_client = redis_async.from_url(config.redis_url)
    publisher = RedisDocumentEventPublisher(
        redis_client=redis_client,
        stream_name=config.ingest_events_stream,
    )

    return DocumentEventDispatcher(publisher, enabled=True)


class IngestionRequest(BaseModel):
    """Request model for POST /ingest endpoint.

    Attributes:
        source_type: Source type enum (web, github, etc.).
        source_target: URL, repo name, or other source identifier.
        limit: Optional maximum pages/items to ingest.
    """

    source_type: SourceType = Field(..., description="Source type for ingestion")
    source_target: str = Field(..., min_length=1, description="URL or source identifier")
    limit: int | None = Field(default=None, ge=1, description="Maximum pages to ingest")


class IngestionJobResponse(BaseModel):
    """Response model for POST /ingest endpoint.

    Attributes:
        job_id: Job UUID.
        state: Current job state.
        source_type: Source type enum.
        source_target: Source identifier.
        created_at: Job creation timestamp (ISO 8601).
    """

    job_id: str
    state: str
    source_type: str
    source_target: str
    created_at: str


class IngestionJobStatus(BaseModel):
    """Response model for GET /ingest/{job_id} endpoint.

    Attributes:
        job_id: Job UUID.
        state: Current job state.
        source_type: Source type enum.
        source_target: Source identifier.
        created_at: Job creation timestamp (ISO 8601).
        started_at: Job start timestamp (ISO 8601, nullable).
        completed_at: Job completion timestamp (ISO 8601, nullable).
        pages_processed: Number of pages processed.
        chunks_created: Number of chunks created.
        errors: List of error objects (nullable).
    """

    job_id: str
    state: str
    source_type: str
    source_target: str
    created_at: str
    started_at: str | None
    completed_at: str | None
    pages_processed: int
    chunks_created: int
    errors: list[dict[str, Any]] | None


def get_ingest_use_case() -> IngestWebUseCase:
    """Dependency factory for IngestWebUseCase.

    Returns:
        IngestWebUseCase: Configured use case instance.
    """
    from packages.clients.postgres_document_store import PostgresDocumentStore
    from packages.common.config import get_config
    from packages.common.db_schema import get_postgres_client

    config = get_config()

    # Initialize adapters
    web_reader = WebReader(
        firecrawl_url=config.firecrawl_api_url,
        firecrawl_api_key=config.firecrawl_api_key.get_secret_value(),
    )
    normalizer = Normalizer()
    chunker = Chunker()
    tei_settings = config.tei_config
    embedder = Embedder(
        tei_url=str(tei_settings.url),
        batch_size=tei_settings.batch_size,
        timeout=float(tei_settings.timeout),
    )
    qdrant_writer = QdrantWriter(
        url=config.qdrant_url,
        collection_name=config.collection_name,
    )

    # Initialize PostgreSQL document store
    pg_conn = get_postgres_client()
    document_store = PostgresDocumentStore(pg_conn)

    dispatcher = _get_event_dispatcher()
    document_callback = None
    if dispatcher is not None:

        def _dispatch(document: DocumentModel, chunk_count: int) -> None:
            dispatcher.dispatch_document_ingested(document, chunk_count=chunk_count)

        document_callback = _dispatch

    return IngestWebUseCase(
        web_reader=web_reader,
        normalizer=normalizer,
        chunker=chunker,
        embedder=embedder,
        qdrant_writer=qdrant_writer,
        document_store=document_store,
        collection_name=config.collection_name,
        flush_threshold=config.ingest_flush_threshold,
        document_ingested_callback=document_callback,
    )


def get_job_store() -> PostgresJobStore:
    """Dependency factory for PostgresJobStore.

    Returns:
        PostgresJobStore: Configured job store instance.
    """
    from packages.common.db_schema import get_postgres_client
    from packages.ingest.postgres_job_store import PostgresJobStore

    pg_conn = get_postgres_client()
    return PostgresJobStore(pg_conn)


async def _execute_ingestion_job(
    job_id: UUID,
    url: str,
    limit: int | None,
    use_case: IngestWebUseCase,
    job_store: PostgresJobStore,
) -> None:
    """Background task to execute ingestion and update job store asynchronously.

    Args:
        job_id: Pre-generated job UUID.
        url: URL to ingest.
        limit: Optional page limit.
        use_case: IngestWebUseCase instance.
        job_store: PostgresJobStore instance.
    """
    try:
        logger.info(f"Starting background ingestion for job {job_id}")
        # Execute use case asynchronously with pre-generated job_id
        completed_job = await use_case.execute(url=url, limit=limit, job_id=job_id)
        # Update job store with final state
        job_store.update(completed_job)
        logger.info(f"Completed background ingestion for job {job_id}")
    except Exception as e:
        logger.exception(f"Background ingestion failed for job {job_id}: {e}")
        # Job state should already be FAILED from use case error handling,
        # but log the error for visibility


@router.post(
    "/",
    response_model=dict[str, Any],
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_api_key)],
)
async def start_ingestion(
    request: Request,
    request_body: IngestionRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Start an ingestion job.

    Creates a PENDING job and queues it for background processing.
    Returns immediately with HTTP 202 Accepted.

    Rate limited to 10 requests per minute.

    Args:
        request: FastAPI request (for rate limiting).
        request_body: Ingestion request with source details.
        background_tasks: FastAPI background tasks.

    Returns:
        ResponseEnvelope[IngestionJobResponse]: Job details in PENDING state.

    Raises:
        HTTPException: 400 if source_type is not supported or URL is invalid.
        RateLimitExceeded: If rate limit exceeded (10/minute).
    """
    from apps.api.schemas.envelope import ResponseEnvelope

    # Apply rate limiting
    limiter = request.app.state.limiter
    await limiter.limit("10/minute")(request)

    # Validate source type
    if request_body.source_type != SourceType.WEB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Source type '{request_body.source_type}' not yet supported. "
                "Only 'web' is currently implemented."
            ),
        )

    # Validate URL for security (SSRF protection)
    try:
        validate_url(request_body.source_target)
    except URLValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid URL: {str(e)}",
        ) from e

    # Generate job ID and create PENDING job
    job_id = uuid4()
    job = IngestionJob(
        job_id=job_id,
        source_type=request_body.source_type,
        source_target=request_body.source_target,
        state=JobState.PENDING,
        created_at=datetime.now(UTC),
        pages_processed=0,
        chunks_created=0,
    )

    # Persist PENDING job immediately
    job_store = get_job_store()
    job_store.create(job)

    # Queue background task to execute ingestion
    use_case = get_ingest_use_case()
    background_tasks.add_task(
        _execute_ingestion_job,
        job_id=job_id,
        url=request_body.source_target,
        limit=request_body.limit,
        use_case=use_case,
        job_store=job_store,
    )

    logger.info(f"Queued ingestion job {job_id} for {request_body.source_target}")

    # Return 202 ACCEPTED with PENDING job
    response_data = IngestionJobResponse(
        job_id=str(job.job_id),
        state=job.state.value,
        source_type=job.source_type.value,
        source_target=job.source_target,
        created_at=job.created_at.isoformat(),
    )
    return ResponseEnvelope(data=response_data, error=None).model_dump()


@router.get("/{job_id}", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
async def get_ingestion_status(job_id: UUID) -> dict[str, Any]:
    """Get ingestion job status.

    Retrieves current status and progress of an ingestion job.

    Args:
        job_id: Job UUID to retrieve.

    Returns:
        ResponseEnvelope[IngestionJobStatus]: Complete job status with progress.

    Raises:
        HTTPException: 404 if job not found.
    """
    from apps.api.schemas.envelope import ResponseEnvelope

    job_store = get_job_store()
    job = job_store.get_by_id(job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    status_data = IngestionJobStatus(
        job_id=str(job.job_id),
        state=job.state.value,
        source_type=job.source_type.value,
        source_target=job.source_target,
        created_at=job.created_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        pages_processed=job.pages_processed,
        chunks_created=job.chunks_created,
        errors=job.errors,
    )
    return ResponseEnvelope(data=status_data, error=None).model_dump()
