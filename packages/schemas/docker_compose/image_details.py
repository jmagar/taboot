"""ImageDetails entity schema.

Represents parsed Docker image details from a Compose service.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ImageDetails(BaseModel):
    """ImageDetails entity representing parsed Docker image information.

    Extracted from Docker Compose service image declarations.

    Examples:
        >>> from datetime import datetime, UTC
        >>> image = ImageDetails(
        ...     image_name="nginx",
        ...     tag="alpine",
        ...     registry="docker.io",
        ...     digest="sha256:abcdef123456",
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="yaml_parser",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> image.image_name
        'nginx'
    """

    # Image fields
    image_name: str = Field(
        ...,
        min_length=1,
        description="Image name (repository name)",
        examples=["nginx", "postgres", "redis", "myapp"],
    )
    tag: str | None = Field(
        None,
        description="Image tag (defaults to 'latest' if not specified)",
        examples=["alpine", "14", "7-alpine", "1.2.3", "latest"],
    )
    registry: str | None = Field(
        None,
        description="Registry hostname (e.g., docker.io, gcr.io, ghcr.io)",
        examples=["docker.io", "gcr.io", "ghcr.io", "registry.example.com"],
    )
    digest: str | None = Field(
        None,
        description="Image digest (SHA256 hash)",
        examples=["sha256:abcdef123456789", "sha256:fedcba987654321"],
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
        examples=["yaml_parser", "docker_compose_reader", "image_parser"],
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
                    "image_name": "nginx",
                    "tag": "alpine",
                    "registry": "docker.io",
                    "digest": "sha256:abcdef123456",
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
