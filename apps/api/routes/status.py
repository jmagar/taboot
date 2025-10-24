"""System status endpoint for Taboot platform.

Provides GET /status endpoint for checking overall system health, service status,
queue depths, and metrics.

Required by FR-046: API MUST provide system status endpoints with health checks.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from redis import asyncio as redis

from apps.api.deps.auth import verify_api_key
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
        logger.exception("Failed to initialize GetStatusUseCase")
        raise RuntimeError("Failed to initialize status dependencies") from e


@router.get(
    "",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_api_key)],
)
async def get_system_status() -> dict[str, Any]:
    """Get overall system status.

    Returns current system status including:
    - Overall health (all services)
    - Per-service health status
    - Queue depths (ingestion, extraction)
    - System metrics snapshot

    Returns:
        ResponseEnvelope[SystemStatusResponse]: System status data or error.

    Raises:
        HTTPException: 500 if status aggregation fails.

    Example:
        >>> response = client.get("/status", headers={"X-API-Key": "test-key"})
        >>> assert response.status_code == 200
        >>> envelope = response.json()
        >>> assert "data" in envelope
        >>> assert "error" in envelope
        >>> data = envelope["data"]
        >>> assert "overall_healthy" in data
        >>> assert "services" in data
        >>> assert "queue_depth" in data
        >>> assert "metrics" in data
    """
    from apps.api.schemas.envelope import ResponseEnvelope

    try:
        # Get use case and execute
        use_case = get_status_use_case()
        system_status: SystemStatus = await use_case.execute()

        # Build response data
        status_data = SystemStatusResponse(
            overall_healthy=system_status.overall_healthy,
            services=system_status.services,
            queue_depth=system_status.queue_depth,
            metrics=system_status.metrics,
        )

        # Return success envelope
        return ResponseEnvelope(data=status_data, error=None).model_dump()

    except Exception as e:
        logger.exception("Status aggregation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Status aggregation failed",
        ) from e
