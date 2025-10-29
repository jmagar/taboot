"""ComposeVolume entity schema.

Represents a volume definition in a Docker Compose file.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ComposeVolume(BaseModel):
    """ComposeVolume entity representing a Docker Compose volume.

    Extracted from Docker Compose YAML files.

    Examples:
        >>> from datetime import datetime, UTC
        >>> volume = ComposeVolume(
        ...     name="data",
        ...     driver="local",
        ...     external=False,
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="yaml_parser",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> volume.name
        'data'
    """

    # Identity fields
    name: str = Field(
        ...,
        min_length=1,
        description="Volume name (key in volumes block)",
        examples=["data", "postgres-data", "app-logs", "config"],
    )

    # Volume configuration (optional)
    driver: str | None = Field(
        None,
        description="Volume driver",
        examples=["local", "nfs", "rexray", "flocker"],
    )
    external: bool | None = Field(
        None,
        description="Whether this is an external volume",
    )
    driver_opts: dict[str, Any] | None = Field(
        None,
        description="Driver-specific options",
        examples=[{"type": "nfs", "device": ":/mnt/data", "o": "addr=192.168.1.1"}],
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
                    "name": "data",
                    "driver": "local",
                    "external": False,
                    "driver_opts": {"type": "none", "device": "/mnt/data", "o": "bind"},
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
