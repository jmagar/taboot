"""GetStatusUseCase - System status aggregation for Taboot platform.

Aggregates system health status from multiple sources:
- Service health (Neo4j, Qdrant, Redis, TEI, Ollama, Firecrawl, Playwright)
- Queue depths (ingestion, extraction)
- System metrics snapshot

Returns partial data on failures (fail-fast within each component, but continue).
"""

import logging
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field
from redis import asyncio as redis

from packages.common.health import SystemHealthStatus

logger = logging.getLogger(__name__)


# ========== Models ==========


class ServiceHealth(BaseModel):
    """Health status for a single service.

    Attributes:
        name: Service name (neo4j, qdrant, redis, etc).
        healthy: True if service is healthy and responsive.
        message: Optional status message or error description.
    """

    name: str = Field(..., description="Service name")
    healthy: bool = Field(..., description="Health status")
    message: str | None = Field(default=None, description="Status or error message")


class QueueDepth(BaseModel):
    """Queue depth statistics.

    Attributes:
        ingestion: Number of items in ingestion queue.
        extraction: Number of items in extraction queue.
    """

    ingestion: int = Field(..., ge=0, description="Ingestion queue depth")
    extraction: int = Field(..., ge=0, description="Extraction queue depth")


class MetricsSnapshot(BaseModel):
    """System metrics snapshot.

    Attributes:
        documents_ingested: Total documents ingested.
        chunks_indexed: Total chunks in vector store.
        extraction_jobs_completed: Total extraction jobs completed.
        graph_nodes_created: Total nodes in graph database.
    """

    documents_ingested: int = Field(..., ge=0, description="Total documents ingested")
    chunks_indexed: int = Field(..., ge=0, description="Total chunks indexed")
    extraction_jobs_completed: int = Field(..., ge=0, description="Extraction jobs completed")
    graph_nodes_created: int = Field(..., ge=0, description="Graph nodes created")


class SystemStatus(BaseModel):
    """Aggregate system status.

    Attributes:
        overall_healthy: True if all services are healthy.
        services: Dictionary mapping service names to health status.
        queue_depth: Queue depth statistics.
        metrics: System metrics snapshot.
    """

    overall_healthy: bool = Field(..., description="Overall system health")
    services: dict[str, ServiceHealth] = Field(..., description="Per-service health status")
    queue_depth: QueueDepth = Field(..., description="Queue depth statistics")
    metrics: MetricsSnapshot = Field(..., description="System metrics snapshot")


# ========== Use Case ==========


class GetStatusUseCase:
    """Use case for aggregating system status.

    Orchestrates status collection from multiple sources:
    - Health checks for all services
    - Queue depth from Redis
    - Metrics snapshot (placeholder for now)

    Partial failures are tolerated - returns available data.
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        health_checker: Callable[[], Any],
    ) -> None:
        """Initialize GetStatusUseCase with dependencies.

        Args:
            redis_client: Redis client for queue depth queries.
            health_checker: Async function to check system health.
        """
        self.redis_client = redis_client
        self.health_checker = health_checker

        logger.info("Initialized GetStatusUseCase")

    async def execute(self) -> SystemStatus:
        """Execute system status aggregation.

        Collects:
        1. Service health status from all services
        2. Queue depths from Redis
        3. System metrics snapshot

        Returns partial data on failures (does not raise exceptions).

        Returns:
            SystemStatus: Aggregated system status.
        """
        logger.info("Executing system status aggregation")

        # Step 1: Check service health
        services, overall_healthy = await self._check_service_health()

        # Step 2: Get queue depths
        queue_depth = await self._get_queue_depth()

        # Step 3: Get metrics snapshot (placeholder)
        metrics = await self._get_metrics_snapshot()

        status = SystemStatus(
            overall_healthy=overall_healthy,
            services=services,
            queue_depth=queue_depth,
            metrics=metrics,
        )

        logger.info(
            f"System status: overall_healthy={overall_healthy}, "
            f"queue_depth=(ingestion={queue_depth.ingestion}, "
            f"extraction={queue_depth.extraction})"
        )

        return status

    async def _check_service_health(self) -> tuple[dict[str, ServiceHealth], bool]:
        """Check health of all services.

        Returns:
            Tuple of (services dict, overall_healthy bool).
        """
        try:
            health_status: SystemHealthStatus = await self.health_checker()
            services = {
                name: ServiceHealth(name=name, healthy=healthy)
                for name, healthy in health_status["services"].items()
            }
            overall_healthy = health_status["healthy"]
            return services, overall_healthy
        except Exception as e:
            logger.error(f"Health check failed: {e}", exc_info=True)
            # Fallback: mark all services as unhealthy
            service_names = ["neo4j", "qdrant", "redis", "tei", "ollama", "firecrawl", "playwright"]
            services = {
                name: ServiceHealth(
                    name=name,
                    healthy=False,
                    message=f"Health check error: {str(e)}",
                )
                for name in service_names
            }
            return services, False

    async def _get_queue_depth(self) -> QueueDepth:
        """Get queue depths from Redis.

        Returns:
            QueueDepth: Queue depth statistics.
        """
        try:
            ingestion_depth = await self.redis_client.llen("queue:ingestion")
            extraction_depth = await self.redis_client.llen("queue:extraction")
            return QueueDepth(
                ingestion=ingestion_depth,
                extraction=extraction_depth,
            )
        except Exception as e:
            logger.error(f"Failed to get queue depths: {e}", exc_info=True)
            # Fallback: return zeros
            return QueueDepth(ingestion=0, extraction=0)

    async def _get_metrics_snapshot(self) -> MetricsSnapshot:
        """Get system metrics snapshot.

        Placeholder implementation - returns zeros.
        TODO: Implement actual metrics collection.

        Returns:
            MetricsSnapshot: System metrics snapshot.
        """
        # Placeholder: return zeros
        # TODO: Query Qdrant for chunks_indexed, Neo4j for graph_nodes_created, etc.
        return MetricsSnapshot(
            documents_ingested=0,
            chunks_indexed=0,
            extraction_jobs_completed=0,
            graph_nodes_created=0,
        )


# Export public API
__all__ = [
    "GetStatusUseCase",
    "SystemStatus",
    "ServiceHealth",
    "QueueDepth",
    "MetricsSnapshot",
]
