"""FastAPI application for Taboot API with CORS, lifecycle management, and middleware."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import redis.asyncio as redis
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from apps.api.middleware.logging import RequestLoggingMiddleware
from apps.api.middleware.metrics import PrometheusMiddleware
from apps.api.routes import documents, extract, ingest, init, metrics, query, status
from packages.common.config import get_config

logger = logging.getLogger(__name__)

# Single source of truth for version
try:
    from importlib.metadata import version as get_version

    VERSION = get_version("taboot")
except Exception:
    # Fallback for development or when package not installed
    VERSION = os.getenv("TABOOT_VERSION", "0.4.0")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle: startup and shutdown.

    Startup:
        - Initialize Redis client with connection pooling
        - Initialize Neo4j driver with connection pooling
        - Initialize Qdrant client with connection pooling
        - Initialize PostgreSQL connection pool
        - Log service readiness

    Shutdown:
        - Close all client connections gracefully
        - Clean up resources
    """
    config = get_config()

    # Startup
    logger.info("Starting Taboot API", extra={"version": VERSION})

    # Initialize Redis with connection pooling
    try:
        redis_pool: redis.ConnectionPool = redis.ConnectionPool.from_url(
            config.redis_url,
            max_connections=config.redis_max_connections,
            socket_timeout=config.redis_socket_timeout,
            health_check_interval=30,
        )
        app.state.redis = redis.Redis(connection_pool=redis_pool)
        logger.info(
            "Redis client initialized with connection pooling",
            extra={
                "url": config.redis_url,
                "max_connections": config.redis_max_connections,
            },
        )
    except Exception as e:
        logger.exception("Failed to initialize Redis client", extra={"error": str(e)})
        raise

    # Initialize Neo4j driver with connection pooling
    try:
        from packages.graph.client import Neo4jClient

        neo4j_client = Neo4jClient()
        neo4j_client.connect()
        app.state.neo4j_client = neo4j_client
        app.state.neo4j_driver = neo4j_client.get_driver()
        logger.info(
            "Neo4j client initialized with connection pooling",
            extra={
                "uri": config.neo4j_uri,
                "max_pool_size": config.neo4j_max_pool_size,
            },
        )
    except Exception as e:
        logger.exception("Failed to initialize Neo4j client", extra={"error": str(e)})
        # Close Redis before re-raising
        if hasattr(app.state, "redis"):
            await app.state.redis.aclose()
        raise

    # Initialize Qdrant client with connection pooling
    try:
        from packages.vector.qdrant_client import QdrantVectorClient

        qdrant_client = QdrantVectorClient(
            url=config.qdrant_url,
            collection_name=config.collection_name,
            embedding_dim=config.qdrant_embedding_dim,
            max_connections=config.qdrant_max_connections,
        )
        app.state.qdrant_client = qdrant_client
        logger.info(
            "Qdrant client initialized with connection pooling",
            extra={
                "url": config.qdrant_url,
                "max_connections": config.qdrant_max_connections,
            },
        )
    except Exception as e:
        logger.exception("Failed to initialize Qdrant client", extra={"error": str(e)})
        # Close existing clients before re-raising
        if hasattr(app.state, "neo4j_client"):
            app.state.neo4j_client.close()
        if hasattr(app.state, "redis"):
            await app.state.redis.aclose()
        raise

    # Initialize PostgreSQL connection pool
    try:
        from packages.common.postgres_pool import PostgresPool

        postgres_pool = PostgresPool(config)
        app.state.postgres_pool = postgres_pool
        logger.info(
            "PostgreSQL connection pool initialized",
            extra={
                "host": config.postgres_host,
                "min_pool_size": config.postgres_min_pool_size,
                "max_pool_size": config.postgres_max_pool_size,
            },
        )
    except Exception as e:
        logger.exception("Failed to initialize PostgreSQL pool", extra={"error": str(e)})
        # Close existing clients before re-raising
        if hasattr(app.state, "qdrant_client"):
            app.state.qdrant_client.close()
        if hasattr(app.state, "neo4j_client"):
            app.state.neo4j_client.close()
        if hasattr(app.state, "redis"):
            await app.state.redis.aclose()
        raise

    logger.info("Taboot API startup complete")

    yield

    # Shutdown
    logger.info("Shutting down Taboot API")

    # Close PostgreSQL pool
    if hasattr(app.state, "postgres_pool"):
        try:
            app.state.postgres_pool.close_all()
            logger.info("PostgreSQL connection pool closed")
        except Exception as e:
            logger.exception("Error closing PostgreSQL pool", extra={"error": str(e)})

    # Close Qdrant client
    if hasattr(app.state, "qdrant_client"):
        try:
            app.state.qdrant_client.close()
            logger.info("Qdrant client closed")
        except Exception as e:
            logger.exception("Error closing Qdrant client", extra={"error": str(e)})

    # Close Neo4j driver
    if hasattr(app.state, "neo4j_client"):
        try:
            app.state.neo4j_client.close()
            logger.info("Neo4j client closed")
        except Exception as e:
            logger.exception("Error closing Neo4j client", extra={"error": str(e)})

    # Close Redis
    if hasattr(app.state, "redis"):
        try:
            await app.state.redis.aclose()
            logger.info("Redis client closed")
        except Exception as e:
            logger.exception("Error closing Redis client", extra={"error": str(e)})

    logger.info("Taboot API shutdown complete")


app = FastAPI(
    title="Taboot API",
    version=VERSION,
    description="Doc-to-Graph RAG Platform",
    lifespan=lifespan,
)

# Initialize rate limiter with Redis backend
config = get_config()
limiter = Limiter(key_func=get_remote_address, storage_uri=config.redis_url)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware
config = get_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_allow_origins,
    allow_credentials="*" not in config.cors_allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Add Prometheus metrics middleware
app.add_middleware(PrometheusMiddleware)

# Register routers
app.include_router(init.router)
app.include_router(ingest.router, prefix="/ingest", tags=["ingestion"])
app.include_router(extract.router, prefix="/extract", tags=["extraction"])
app.include_router(query.router, tags=["query"])
app.include_router(status.router, prefix="/status", tags=["status"])
app.include_router(documents.router, tags=["documents"])
app.include_router(metrics.router)


@app.get("/health")
async def health(response: Response) -> dict[str, Any]:
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
        ResponseEnvelope[dict]: Health status with overall status and per-service status.
            - 200 if all services healthy
            - 503 if any service unhealthy
    """
    from fastapi import status as http_status

    from apps.api.schemas.envelope import ResponseEnvelope
    from packages.common.health import check_system_health

    health_status = await check_system_health()

    is_healthy = health_status.get("healthy", False)
    response.status_code = (
        http_status.HTTP_200_OK if is_healthy else http_status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return ResponseEnvelope(
        data=health_status,
        error=None if is_healthy else "UNHEALTHY",
    ).model_dump()


@app.get("/")
async def root() -> dict[str, dict[str, str] | None]:
    """Root endpoint.

    Returns:
        ResponseEnvelope[dict]: API info with version and docs link.
    """
    from apps.api.schemas.envelope import ResponseEnvelope

    return ResponseEnvelope(
        data={"message": f"Taboot API v{VERSION}", "docs": "/docs"},
        error=None,
    ).model_dump()
