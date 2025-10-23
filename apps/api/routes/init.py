"""System initialization endpoint.

Provides POST /init endpoint for initializing Neo4j constraints, Qdrant collections,
and PostgreSQL schema. Verifies system health before and after initialization.

Required by FR-032: System MUST provide /init endpoint with health verification.
"""

import logging
from collections.abc import Mapping
from typing import TypedDict

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

# Import modules instead of functions to support test mocking at package level
import packages.common.db_schema
import packages.common.health
import packages.graph.constraints
import packages.vector.collections

logger = logging.getLogger(__name__)
router = APIRouter()


class SystemHealthPayload(TypedDict):
    """Health payload from system health check.

    Attributes:
        healthy: Overall system health status.
        services: Per-service health status mapping.
    """

    healthy: bool
    services: Mapping[str, bool]


class InitResponse(BaseModel):
    """Response model for /init endpoint.

    Attributes:
        status: Initialization status ("initialized" on success).
        message: Human-readable status message.
        services: System health status with healthy flag and per-service breakdown.
    """

    status: str
    message: str
    services: SystemHealthPayload


@router.post("/init", status_code=status.HTTP_200_OK)
async def initialize_system() -> dict[str, object]:
    """Initialize system schemas and collections.

    Performs the following initialization steps:
    1. Create Neo4j constraints
    2. Create Qdrant collections
    3. Create PostgreSQL schema
    4. Check system health after init

    Returns:
        dict: Envelope with initialized payload and post-init health status.

    Raises:
        HTTPException: 500 if any initialization step fails.

    Example:
        >>> response = client.post("/init")
        >>> assert response.status_code == 200
        >>> data = response.json()
        >>> assert data["data"]["status"] == "initialized"
    """
    logger.info("System initialization started")

    try:
        # Create Neo4j constraints
        logger.debug("Creating Neo4j constraints")
        await packages.graph.constraints.create_neo4j_constraints()

        # Create Qdrant collections
        logger.debug("Creating Qdrant collections")
        await packages.vector.collections.create_qdrant_collections()

        # Create PostgreSQL schema
        logger.debug("Creating PostgreSQL schema")
        await packages.common.db_schema.create_postgresql_schema()

        # Check system health after initialization
        logger.debug("Checking post-init system health")
        health = await packages.common.health.check_system_health()

        # Build response payload
        response_data = {
            "status": "initialized",
            "message": "System initialized successfully",
            "services": health,
        }

        logger.info("System initialization completed successfully")

        return {
            "data": response_data,
            "error": None,
        }

    except Exception as e:
        # Log initialization failure with context
        logger.exception("System initialization failed")

        # Return error envelope
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "initialization_failed",
                    "message": f"System initialization failed: {e!s}",
                }
            },
        ) from e
