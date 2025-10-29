"""HealthCheck entity schema.

Represents a health check configuration for a Docker Compose service.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class HealthCheck(BaseModel):
    """HealthCheck entity representing a Docker health check configuration.

    Extracted from Docker Compose service healthcheck declarations.

    Examples:
        >>> from datetime import datetime, UTC
        >>> health = HealthCheck(
        ...     test="CMD-SHELL curl -f http://localhost/ || exit 1",
        ...     interval="30s",
        ...     timeout="10s",
        ...     retries=3,
        ...     start_period="60s",
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="yaml_parser",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> health.interval
        '30s'
    """

    # Health check fields
    test: str = Field(
        ...,
        min_length=1,
        description="Health check test command (CMD, CMD-SHELL, or list)",
        examples=[
            "CMD-SHELL curl -f http://localhost/ || exit 1",
            "CMD pg_isready -U postgres",
            "CMD redis-cli ping",
        ],
    )
    interval: str | None = Field(
        None,
        description="Time between health checks (duration string)",
        examples=["30s", "1m", "2m30s"],
    )
    timeout: str | None = Field(
        None,
        description="Timeout for each health check (duration string)",
        examples=["10s", "30s", "1m"],
    )
    retries: int | None = Field(
        None,
        ge=1,
        description="Number of consecutive failures needed to consider unhealthy",
        examples=[3, 5, 10],
    )
    start_period: str | None = Field(
        None,
        description="Initialization time before health checks count toward retries",
        examples=["60s", "2m", "5m"],
    )

    # Temporal tracking (required on ALL entities)
    created_at: datetime = Field(
        ...,
        description="When we created this node in our system",
    )
    updated_at: datetime = Field(
        ...,
        description="When we last modified this node",
    )
    source_timestamp: datetime | None = Field(
        None,
        description="When the source content was created (if available from source)",
    )

    # Extraction metadata (required on ALL entities)
    extraction_tier: Literal["A", "B", "C"] = Field(
        ...,
        description="Extraction tier: A (deterministic), B (spaCy), C (LLM)",
    )
    extraction_method: str = Field(
        ...,
        description="Method used for extraction",
        examples=["yaml_parser", "docker_compose_reader"],
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Extraction confidence (0.0-1.0, usually 1.0 for Tier A)",
    )
    extractor_version: str = Field(
        ...,
        description="Version of the extractor that created this entity",
        examples=["1.0.0", "1.2.0"],
    )

    @field_validator("extraction_tier")
    @classmethod
    def validate_extraction_tier(cls, v: str) -> str:
        """Validate extraction_tier is A, B, or C."""
        if v not in ("A", "B", "C"):
            raise ValueError("extraction_tier must be A, B, or C")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "test": "CMD-SHELL curl -f http://localhost/ || exit 1",
                    "interval": "30s",
                    "timeout": "10s",
                    "retries": 3,
                    "start_period": "60s",
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "extraction_tier": "A",
                    "extraction_method": "yaml_parser",
                    "confidence": 1.0,
                    "extractor_version": "1.0.0",
                }
            ]
        }
    }
