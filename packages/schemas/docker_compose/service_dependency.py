"""ServiceDependency entity schema.

Represents a dependency relationship between Docker Compose services.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ServiceDependency(BaseModel):
    """ServiceDependency entity representing a service dependency declaration.

    Extracted from Docker Compose service depends_on declarations.

    Examples:
        >>> from datetime import datetime, UTC
        >>> dep = ServiceDependency(
        ...     source_service="web",
        ...     target_service="db",
        ...     condition="service_healthy",
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="yaml_parser",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> dep.target_service
        'db'
    """

    # Dependency fields
    source_service: str = Field(
        ...,
        min_length=1,
        description="Service that depends on another (dependent)",
        examples=["web", "api", "worker"],
    )
    target_service: str = Field(
        ...,
        min_length=1,
        description="Service being depended on (dependency)",
        examples=["db", "redis", "postgres", "rabbitmq"],
    )
    condition: str | None = Field(
        None,
        description="Dependency condition (service_started, service_healthy, service_completed_successfully)",
        examples=["service_started", "service_healthy", "service_completed_successfully"],
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
                    "source_service": "web",
                    "target_service": "db",
                    "condition": "service_healthy",
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
