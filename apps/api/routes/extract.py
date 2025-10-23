"""Extraction endpoints for document extraction processing.

Provides POST /extract/pending and GET /extract/status endpoints for triggering
and monitoring extraction jobs.

Required by FR-045: API MUST provide extraction endpoints with job tracking.
"""

import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from redis import asyncio as redis

from packages.common.health import check_system_health
from packages.core.use_cases.extract_pending import ExtractPendingUseCase
from packages.core.use_cases.get_status import (
    GetStatusUseCase,
    MetricsSnapshot,
    QueueDepth,
    ServiceHealth,
    SystemStatus,
)
from packages.extraction.orchestrator import ExtractionOrchestrator
from packages.extraction.tier_a import parsers
from packages.extraction.tier_a.patterns import EntityPatternMatcher
from packages.extraction.tier_b.window_selector import WindowSelector
from packages.extraction.tier_c.llm_client import TierCLLMClient

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


def get_extract_use_case() -> ExtractPendingUseCase:
    """Dependency factory for ExtractPendingUseCase.

    Returns:
        ExtractPendingUseCase: Configured use case instance.

    Raises:
        RuntimeError: If required dependencies cannot be initialized.
    """
    from packages.common.config import get_config

    config = get_config()

    try:
        # Initialize Redis client (async)
        redis_client = redis.from_url(config.redis_url, decode_responses=True)

        # Initialize Tier A components
        # Use parsers module directly (has parse_code_blocks, parse_tables functions)
        tier_a_patterns = EntityPatternMatcher()

        # Initialize Tier B window selector
        window_selector = WindowSelector()

        # Initialize Tier C LLM client
        llm_client = TierCLLMClient(
            model="qwen3:4b",
            redis_client=redis_client,
            batch_size=16,
            temperature=0.0,
        )

        # Initialize ExtractionOrchestrator
        orchestrator = ExtractionOrchestrator(
            tier_a_parser=parsers,  # Module with parse_code_blocks, parse_tables functions
            tier_a_patterns=tier_a_patterns,
            window_selector=window_selector,
            llm_client=llm_client,
            redis_client=redis_client,
        )

        # Stub DocumentStore for now
        # TODO: Replace with actual PostgreSQL adapter
        from uuid import UUID

        from packages.core.use_cases.extract_pending import DocumentStore
        from packages.schemas.models import Document

        class StubDocumentStore(DocumentStore):
            """Stub DocumentStore for MVP."""

            def query_pending(self, limit: int | None = None) -> list[Document]:
                """Return empty list - no pending documents."""
                return []

            def get_content(self, doc_id: UUID) -> str:
                """Return empty content."""
                return ""

            def update_document(self, document: Document) -> None:
                """No-op update."""

        document_store = StubDocumentStore()

        return ExtractPendingUseCase(
            orchestrator=orchestrator,
            document_store=document_store,
        )

    except Exception as e:
        logger.exception("Failed to initialize ExtractPendingUseCase: %s", e)
        raise RuntimeError(f"Failed to initialize extraction dependencies: {e}") from e


@router.post("/pending", response_model=ExtractionResponse, status_code=status.HTTP_200_OK)
async def trigger_extraction(
    limit: int | None = Query(None, ge=1, description="Maximum documents to process"),
) -> ExtractionResponse:
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
        # Get use case and execute
        use_case = get_extract_use_case()
        result = await use_case.execute(limit=limit)

        # Return response
        return ExtractionResponse(
            processed=result["processed"],
            succeeded=result["succeeded"],
            failed=result["failed"],
        )

    except Exception as e:
        logger.exception("Extraction pipeline failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Extraction pipeline failed: {str(e)}",
        ) from e


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


@router.get("/status", response_model=SystemStatusResponse, status_code=status.HTTP_200_OK)
async def get_extraction_status() -> SystemStatusResponse:
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
