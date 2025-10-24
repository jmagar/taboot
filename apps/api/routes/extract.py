"""Extraction endpoints for document extraction processing.

Provides POST /extract/pending and GET /extract/status endpoints for triggering
and monitoring extraction jobs.

Required by FR-045: API MUST provide extraction endpoints with job tracking.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from apps.api.deps import get_extract_use_case, get_status_use_case, verify_api_key
from apps.api.schemas import ResponseEnvelope
from packages.core.use_cases.extract_pending import ExtractPendingUseCase
from packages.core.use_cases.get_status import (
    GetStatusUseCase,
    MetricsSnapshot,
    QueueDepth,
    ServiceHealth,
    SystemStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class ExtractionResponse(BaseModel):
    """Response model for POST /extract/pending endpoint.

    Attributes:
        processed: Total documents attempted.
        succeeded: Documents successfully extracted.
        failed: Documents that failed extraction.
    """

    processed: int = Field(..., ge=0, description="Total documents processed")
    succeeded: int = Field(..., ge=0, description="Documents successfully extracted")
    failed: int = Field(..., ge=0, description="Documents that failed extraction")


class SystemStatusResponse(BaseModel):
    """Response model for GET /extract/status endpoint.

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


@router.post(
    "/pending",
    response_model=ResponseEnvelope[ExtractionResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_api_key)],
)
async def trigger_extraction(
    limit: int | None = Query(None, ge=1, description="Maximum documents to process"),
    *,
    use_case: Annotated[ExtractPendingUseCase, Depends(get_extract_use_case)],
) -> ResponseEnvelope[ExtractionResponse]:
    """Trigger extraction for pending documents.

    Processes documents in PENDING extraction state through the multi-tier
    extraction pipeline (Tier A → B → C).

    Args:
        limit: Optional maximum number of documents to process.

    Returns:
        ExtractionResponse: Summary statistics with processed/succeeded/failed counts.

    Raises:
        HTTPException: 500 if extraction pipeline fails.

    Example:
        >>> response = client.post("/extract/pending?limit=10")
        >>> assert response.status_code == 200
        >>> data = response.json()
        >>> assert "processed" in data
        >>> assert "succeeded" in data
        >>> assert "failed" in data
    """
    try:
        result = await use_case.execute(limit=limit)
    except (ConnectionError, TimeoutError) as e:
        # Service connectivity issues (Redis, Neo4j, Qdrant, PostgreSQL)
        logger.exception("Service connection failed during extraction")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"External service unavailable: {str(e)}",
        ) from e
    except (KeyError, ValueError) as e:
        # Data validation or integrity issues
        logger.exception("Data validation error during extraction")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Data processing error: {str(e)}",
        ) from e
    except Exception as e:
        # Unexpected errors - log with full context
        logger.exception("Unexpected extraction pipeline error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during extraction",
        ) from e
    else:
        payload = ExtractionResponse(
            processed=result["processed"],
            succeeded=result["succeeded"],
            failed=result["failed"],
        )
        return ResponseEnvelope(data=payload, error=None)


@router.get(
    "/status",
    response_model=ResponseEnvelope[SystemStatusResponse],
    status_code=status.HTTP_200_OK,
)
async def get_extraction_status(
    *,
    use_case: Annotated[GetStatusUseCase, Depends(get_status_use_case)],
) -> ResponseEnvelope[SystemStatusResponse]:
    """Get extraction system status.

    Returns current extraction system status including:
    - Overall health (all services)
    - Per-service health status
    - Queue depths (ingestion, extraction)
    - System metrics snapshot

    Returns:
        SystemStatusResponse: Complete system status.

    Raises:
        HTTPException: 500 if status aggregation fails.

    Example:
        >>> response = client.get("/extract/status")
        >>> assert response.status_code == 200
        >>> data = response.json()
        >>> assert "overall_healthy" in data
        >>> assert "services" in data
        >>> assert "queue_depth" in data
        >>> assert "metrics" in data
    """
    try:
        # Get use case and execute
        system_status: SystemStatus = await use_case.execute()

        # Return response
        payload = SystemStatusResponse(
            overall_healthy=system_status.overall_healthy,
            services=system_status.services,
            queue_depth=system_status.queue_depth,
            metrics=system_status.metrics,
        )
        return ResponseEnvelope(data=payload, error=None)
    except (ConnectionError, TimeoutError) as e:
        # Service connectivity issues (Redis, Neo4j, Qdrant, PostgreSQL)
        logger.exception("Service connection failed during status check")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cannot check system status: {str(e)}",
        ) from e
    except Exception as e:
        # Unexpected errors - log with full context
        logger.exception("Unexpected error during status aggregation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during status check",
        ) from e
