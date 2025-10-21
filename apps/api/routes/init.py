"""System initialization endpoint.

Provides POST /init endpoint for initializing Neo4j constraints, Qdrant collections,
and PostgreSQL schema. Verifies system health before and after initialization.

Required by FR-032: System MUST provide /init endpoint with health verification.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

# Import modules instead of functions to support test mocking at package level
import packages.common.db_schema
import packages.common.health
import packages.graph.constraints
import packages.vector.collections

router = APIRouter()


class InitResponse(BaseModel):
    """Response model for /init endpoint.

    Attributes:
        status: Initialization status ("initialized" on success).
        message: Human-readable status message.
        services: System health status with healthy flag and per-service breakdown.
    """

    status: str
    message: str
    services: dict[str, Any]


@router.post("/init", response_model=InitResponse, status_code=status.HTTP_200_OK)
async def initialize_system() -> InitResponse:
    """Initialize system schemas and collections.

    Performs the following initialization steps:
    1. Check system health
    2. Create Neo4j constraints
    3. Create Qdrant collections
    4. Create PostgreSQL schema

    Returns:
        InitResponse: Status, message, and health breakdown.

    Raises:
        HTTPException: 500 if any initialization step fails.

    Example:
        >>> response = client.post("/init")
        >>> assert response.status_code == 200
        >>> assert response.json()["status"] == "initialized"
    """
    # Check system health first
    health = await packages.common.health.check_system_health()

    try:
        # Create Neo4j constraints
        await packages.graph.constraints.create_neo4j_constraints()

        # Create Qdrant collections
        await packages.vector.collections.create_qdrant_collections()

        # Create PostgreSQL schema
        await packages.common.db_schema.create_postgresql_schema()

    except Exception as e:
        # If initialization fails, return 500 with error details
        error_msg = str(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"System initialization failed: {error_msg}",
        ) from e

    # Return success response with health status (cast TypedDict to dict for Pydantic)
    return InitResponse(
        status="initialized",
        message="System initialized successfully",
        services=dict(health),
    )
