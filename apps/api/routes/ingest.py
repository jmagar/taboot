"""Ingestion endpoints for web crawling and document ingestion.

Provides POST /ingest and GET /ingest/{job_id} endpoints for creating and
monitoring ingestion jobs.

Required by FR-033: API MUST provide ingestion endpoints with job tracking.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from packages.core.use_cases.ingest_web import IngestWebUseCase
from packages.ingest.chunker import Chunker
from packages.ingest.embedder import Embedder
from packages.ingest.normalizer import Normalizer
from packages.ingest.readers.web import WebReader
from packages.schemas.models import IngestionJob, SourceType
from packages.vector.writer import QdrantWriter

router = APIRouter()

# In-memory job store for MVP (TODO: Replace with persistent storage)
_job_store: dict[UUID, IngestionJob] = {}


class IngestionRequest(BaseModel):
    """Request model for POST /ingest endpoint.

    Attributes:
        source_type: Source type enum (web, github, etc.).
        source_target: URL, repo name, or other source identifier.
        limit: Optional maximum pages/items to ingest.
    """

    source_type: SourceType = Field(
        ..., description="Source type for ingestion"
    )
    source_target: str = Field(
        ..., min_length=1, description="URL or source identifier"
    )
    limit: int | None = Field(
        default=None, ge=1, description="Maximum pages to ingest"
    )


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
    from packages.common.config import get_config
    from packages.common.db_schema import get_postgres_client
    from packages.common.postgres_document_store import PostgresDocumentStore

    config = get_config()

    # Initialize adapters
    web_reader = WebReader(
        firecrawl_url=config.firecrawl_api_url,
        firecrawl_api_key=config.firecrawl_api_key,
    )
    normalizer = Normalizer()
    chunker = Chunker()
    embedder = Embedder(tei_url=config.tei_embedding_url)
    qdrant_writer = QdrantWriter(
        url=config.qdrant_url,
        collection_name=config.collection_name,
    )

    # Initialize PostgreSQL document store
    pg_conn = get_postgres_client()
    document_store = PostgresDocumentStore(pg_conn)

    return IngestWebUseCase(
        web_reader=web_reader,
        normalizer=normalizer,
        chunker=chunker,
        embedder=embedder,
        qdrant_writer=qdrant_writer,
        document_store=document_store,
        collection_name=config.collection_name,
    )


def get_job_by_id(job_id: UUID) -> IngestionJob | None:
    """Retrieve job from job store by ID.

    Args:
        job_id: Job UUID to retrieve.

    Returns:
        IngestionJob if found, None otherwise.
    """
    return _job_store.get(job_id)


@router.post("/", response_model=IngestionJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_ingestion(request: IngestionRequest) -> IngestionJobResponse:
    """Start an ingestion job.

    Creates and executes an ingestion job for the specified source.
    Currently only supports web source type.

    Args:
        request: Ingestion request with source details.

    Returns:
        IngestionJobResponse: Created job details.

    Raises:
        HTTPException: 400 if source_type is not supported.

    Example:
        >>> response = client.post("/ingest", json={
        ...     "source_type": "web",
        ...     "source_target": "https://example.com",
        ...     "limit": 20
        ... })
        >>> assert response.status_code == 202
        >>> assert response.json()["state"] == "pending"
    """
    # Validate source type
    if request.source_type != SourceType.WEB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Source type '{request.source_type}' not yet supported. "
                "Only 'web' is currently implemented."
            ),
        )

    # Get use case and execute
    use_case = get_ingest_use_case()
    job = use_case.execute(url=request.source_target, limit=request.limit)

    # Store job for retrieval
    _job_store[job.job_id] = job

    # Return response
    return IngestionJobResponse(
        job_id=str(job.job_id),
        state=job.state.value,
        source_type=job.source_type.value,
        source_target=job.source_target,
        created_at=job.created_at.isoformat(),
    )


@router.get("/{job_id}", response_model=IngestionJobStatus, status_code=status.HTTP_200_OK)
async def get_ingestion_status(job_id: UUID) -> IngestionJobStatus:
    """Get ingestion job status.

    Retrieves current status and progress of an ingestion job.

    Args:
        job_id: Job UUID to retrieve.

    Returns:
        IngestionJobStatus: Complete job status with progress.

    Raises:
        HTTPException: 404 if job not found.

    Example:
        >>> response = client.get(f"/ingest/{job_id}")
        >>> assert response.status_code == 200
        >>> data = response.json()
        >>> assert "pages_processed" in data
        >>> assert "chunks_created" in data
    """
    job = get_job_by_id(job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    return IngestionJobStatus(
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
