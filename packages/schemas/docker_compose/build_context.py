"""BuildContext entity schema.

Represents a build context configuration for a Docker Compose service.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class BuildContext(BaseModel):
    """BuildContext entity representing a Docker build configuration.

    Extracted from Docker Compose service build declarations.

    Examples:
        >>> from datetime import datetime, UTC
        >>> build = BuildContext(
        ...     context_path="./api",
        ...     dockerfile="Dockerfile.prod",
        ...     target="production",
        ...     args={"NODE_ENV": "production"},
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="yaml_parser",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> build.context_path
        './api'
    """

    # Build configuration fields
    context_path: str = Field(
        ...,
        min_length=1,
        description="Build context path (relative or absolute)",
        examples=[".", "./api", "./services/web", "/opt/app"],
    )
    dockerfile: str | None = Field(
        None,
        description="Alternative Dockerfile name",
        examples=["Dockerfile", "Dockerfile.prod", "Dockerfile.dev"],
    )
    target: str | None = Field(
        None,
        description="Build stage to target (for multi-stage builds)",
        examples=["production", "development", "builder", "runtime"],
    )
    args: dict[str, Any] | None = Field(
        None,
        description="Build arguments (ARG values)",
        examples=[{"NODE_ENV": "production", "VERSION": "1.2.3", "BUILD_DATE": "2024-01-15"}],
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
                    "context_path": "./api",
                    "dockerfile": "Dockerfile.prod",
                    "target": "production",
                    "args": {"NODE_ENV": "production", "VERSION": "1.2.3"},
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
