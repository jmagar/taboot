"""FastAPI application for Taboot API with CORS, lifecycle management, and middleware."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.middleware import RequestLoggingMiddleware
from apps.api.routes import documents, extract, ingest, init, query, status
from packages.common.config import get_config

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle: startup and shutdown.

    Startup:
        - Initialize Redis client for caching and job queues
        - Log service readiness

    Shutdown:
        - Close Redis connections gracefully
        - Clean up resources
    """
    config = get_config()

    # Startup
    logger.info("Starting Taboot API", extra={"version": "0.4.0"})

    try:
        redis_client = redis.from_url(
            config.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        app.state.redis = redis_client
        logger.info("Redis client initialized", extra={"url": config.redis_url})
    except Exception as e:
        logger.exception("Failed to initialize Redis client", extra={"error": str(e)})
        raise

    logger.info("Taboot API startup complete")

    yield

    # Shutdown
    logger.info("Shutting down Taboot API")

    if hasattr(app.state, "redis"):
        await app.state.redis.aclose()
        logger.info("Redis client closed")

    logger.info("Taboot API shutdown complete")


app = FastAPI(
    title="Taboot API",
    version="0.4.0",
    description="Doc-to-Graph RAG Platform",
    lifespan=lifespan,
)

# Add CORS middleware
config = get_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_allow_origins,
    allow_credentials=False if "*" in config.cors_allow_origins else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Register routers
app.include_router(init.router)
app.include_router(ingest.router, prefix="/ingest", tags=["ingestion"])
app.include_router(extract.router, prefix="/extract", tags=["extraction"])
app.include_router(query.router, tags=["query"])
app.include_router(status.router, prefix="/status", tags=["status"])
app.include_router(documents.router, tags=["documents"])


@app.get("/health")
async def health() -> dict:
    """Health check endpoint with service validation.

    Checks connectivity to all critical services:
    - Neo4j (graph database)
    - Qdrant (vector database)
    - Redis (cache and queues)
    - TEI (embeddings)
    - Ollama (LLM)
    - Firecrawl (web crawler)
    - Playwright (browser automation)

    Returns:
        dict: Health status with overall status and per-service status.
            - 200 if all services healthy
            - 503 if any service unhealthy
    """
    from fastapi import status as http_status
    from fastapi.responses import JSONResponse

    from packages.common.health import check_system_health

    health_status = await check_system_health()

    is_healthy = health_status.get("healthy", False)
    status_code = (
        http_status.HTTP_200_OK
        if is_healthy
        else http_status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return JSONResponse(
        content={
            "data": health_status,
            "error": None if is_healthy else "UNHEALTHY",
        },
        status_code=status_code,
    )


@app.get("/")
async def root() -> dict[str, dict[str, str] | None]:
    """Root endpoint."""
    return {
        "data": {"message": "Taboot API v0.4.0", "docs": "/docs"},
        "error": None,
    }
