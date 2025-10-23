"""System status endpoint for Taboot platform.

Provides GET /status endpoint for checking overall system health, service status,
queue depths, and metrics.

Required by FR-046: API MUST provide system status endpoints with health checks.
"""

import logging
import os

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from redis import asyncio as redis

from packages.common.health import check_system_health
from packages.core.use_cases.get_status import (
    GetStatusUseCase,
    MetricsSnapshot,
    QueueDepth,
    ServiceHealth,
    SystemStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class SystemStatusResponse(BaseModel):
    """Response model for GET /status endpoint.

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


def get_status_use_case() -> GetStatusUseCase:
    """Dependency factory for GetStatusUseCase.

    Returns:
        GetStatusUseCase: Configured use case instance.

    Raises:
        RuntimeError: If required dependencies cannot be initialized.
    """
    from packages.common.config import get_config

    config = get_config()

    try:
        # Initialize Redis client (async)
        redis_client = redis.from_url(config.redis_url, decode_responses=True)

        return GetStatusUseCase(
            redis_client=redis_client,
            health_checker=check_system_health,
        )

    except Exception as e:
        logger.error(f"Failed to initialize GetStatusUseCase: {e}", exc_info=True)
        raise RuntimeError(f"Failed to initialize status dependencies: {e}") from e


@router.get("", response_model=SystemStatusResponse, status_code=status.HTTP_200_OK)
async def get_system_status() -> SystemStatusResponse:
    """Get overall system status.

    Returns current system status including:
    - Overall health (all services)
    - Per-service health status
    - Queue depths (ingestion, extraction)
    - System metrics snapshot

    Returns:
        SystemStatusResponse: Complete system status.

    Raises:
        HTTPException: 500 if status aggregation fails.

    Example:
        >>> response = client.get("/status")
        >>> assert response.status_code == 200
        >>> data = response.json()
        >>> assert "overall_healthy" in data
        >>> assert "services" in data
        >>> assert "queue_depth" in data
        >>> assert "metrics" in data
    """
    try:
        # Get use case and execute
        use_case = get_status_use_case()
        system_status: SystemStatus = await use_case.execute()

        # Return response
        return SystemStatusResponse(
            overall_healthy=system_status.overall_healthy,
            services=system_status.services,
            queue_depth=system_status.queue_depth,
            metrics=system_status.metrics,
        )

    except Exception as e:
        logger.error(f"Status aggregation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Status aggregation failed: {str(e)}",
        ) from e
