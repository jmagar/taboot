"""ComposeProject entity schema.

Represents a Docker Compose project configuration.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ComposeProject(BaseModel):
    """ComposeProject entity representing a Docker Compose project.

    Extracted from Docker Compose YAML files.

    Examples:
        >>> from datetime import datetime, UTC
        >>> project = ComposeProject(
        ...     name="my-project",
        ...     version="3.8",
        ...     file_path="/home/user/docker-compose.yml",
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="yaml_parser",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> project.name
        'my-project'
    """

    # Identity fields
    name: str = Field(
        ...,
        min_length=1,
        description="Project name (from COMPOSE_PROJECT_NAME or derived from directory)",
        examples=["my-project", "taboot", "production-stack"],
    )

    # Project metadata (optional)
    version: str | None = Field(
        None,
        description="Docker Compose file format version",
        examples=["3.8", "3.9", "2.4"],
    )
    file_path: str = Field(
        ...,
        min_length=1,
        description="Path to the Docker Compose file",
        examples=["/opt/docker-compose.yml", "./compose.yaml"],
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
                    "name": "my-project",
                    "version": "3.8",
                    "file_path": "/home/user/docker-compose.yml",
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
