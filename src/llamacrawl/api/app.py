"""FastAPI application surface for orchestrating LlamaCrawl ingestion jobs."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

from llamacrawl.api.job_store import FirecrawlJobStore
from llamacrawl.api.manager import FirecrawlJobManager
from llamacrawl.api.models import (
    FirecrawlJobCreateRequest,
    FirecrawlJobCreateResponse,
    FirecrawlJobDetailResponse,
)
from llamacrawl.api.sessions_manager import SessionsWatcherManager
from llamacrawl.cli.dependencies import build_redis
from llamacrawl.config import load_config
from llamacrawl.embeddings.tei import TEIEmbedding
from llamacrawl.storage.neo4j import Neo4jClient
from llamacrawl.storage.qdrant import QdrantClient
from llamacrawl.utils.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="LlamaCrawl API",
    version="0.1.0",
    description="REST API for submitting and monitoring Firecrawl ingestion jobs.",
)

try:
    _config = load_config()
    _redis_client = build_redis(_config)
    _job_store = FirecrawlJobStore(_redis_client)

    # Initialize heavy clients once for sharing between managers
    _neo4j_client = Neo4jClient(config=_config)
    _qdrant_client = QdrantClient(
        url=_config.qdrant_url,
        collection_name=_config.vector_store.collection_name,
        vector_dimension=_config.vector_store.vector_dimension,
        distance_metric=_config.vector_store.distance_metric,
    )
    _embed_model = TEIEmbedding(base_url=_config.tei_embedding_url)

    # Initialize Firecrawl job manager
    _job_manager = FirecrawlJobManager(
        config=_config,
        redis_client=_redis_client,
        job_store=_job_store,
        qdrant_client=_qdrant_client,
        neo4j_client=_neo4j_client,
        embed_model=_embed_model,
    )

    # Initialize sessions watcher manager if enabled
    _sessions_manager = SessionsWatcherManager(
        config=_config,
        redis_client=_redis_client,
        qdrant_client=_qdrant_client,
        neo4j_client=_neo4j_client,
        embed_model=_embed_model,
    ) if _config.sources.sessions.enabled else None

except Exception:  # pragma: no cover - startup failure is fatal
    logger.exception("Failed to initialize LlamaCrawl API dependencies")
    raise


@app.on_event("startup")
async def _startup() -> None:
    """Initialize background tasks and watchers."""
    if _sessions_manager:
        await _sessions_manager.start()


@app.on_event("shutdown")
async def _shutdown() -> None:
    """Clean up background tasks and shared resources."""
    await _job_manager.shutdown()
    if _sessions_manager:
        await _sessions_manager.shutdown()
    if _neo4j_client:
        _neo4j_client.close()
    _redis_client.close()


@app.post(
    "/firecrawl/crawls",
    response_model=FirecrawlJobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_firecrawl_job(
    request: FirecrawlJobCreateRequest,
) -> FirecrawlJobCreateResponse:
    """Submit a new Firecrawl crawl request."""
    record = await _job_manager.submit_job(request)
    return FirecrawlJobCreateResponse(job_id=record.job_id, status=record.status)


@app.get(
    "/firecrawl/crawls/{job_id}",
    response_model=FirecrawlJobDetailResponse,
)
async def get_firecrawl_job(job_id: str) -> FirecrawlJobDetailResponse:
    """Retrieve current status for a Firecrawl ingestion job."""
    record = _job_store.get(job_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found",
        )
    return FirecrawlJobDetailResponse.from_record(record)


@app.get("/health")
async def health() -> JSONResponse:
    """Basic health probe."""
    redis_ok = _redis_client.health_check()
    status_code = status.HTTP_200_OK if redis_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if redis_ok else "degraded",
            "redis": redis_ok,
        },
    )


__all__ = ["app"]
