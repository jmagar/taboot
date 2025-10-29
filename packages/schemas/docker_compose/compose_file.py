"""ComposeFile entity schema.

Represents a Docker Compose file root entity.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ComposeFile(BaseModel):
    """ComposeFile entity representing a Docker Compose file.

    Extracted from Docker Compose YAML files.

    Examples:
        >>> from datetime import datetime, UTC
        >>> compose_file = ComposeFile(
        ...     file_path="/home/user/project/docker-compose.yml",
        ...     version="3.8",
        ...     project_name="my-project",
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="yaml_parser",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> compose_file.file_path
        '/home/user/project/docker-compose.yml'
    """

    # Identity fields
    file_path: str = Field(
        ...,
        min_length=1,
        description="Absolute or relative path to the Docker Compose file",
        examples=[
            "/home/user/project/docker-compose.yml",
            "./docker-compose.prod.yml",
            "compose.yaml",
        ],
    )

    # Compose file metadata (optional)
    version: str | None = Field(
        None,
        description="Docker Compose file format version",
        examples=["3.8", "3.9", "2.4"],
    )
    project_name: str | None = Field(
        None,
        description="Project name (from COMPOSE_PROJECT_NAME or directory name)",
        examples=["my-project", "taboot", "production-stack"],
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
        description="When the source content was created (file mtime if available)",
    )

    # Extraction metadata (required on ALL entities)
    extraction_tier: Literal["A", "B", "C"] = Field(
        ...,
        description="Extraction tier: A (deterministic), B (spaCy), C (LLM)",
    )
    extraction_method: str = Field(
        ...,
        description="Method used for extraction",
        examples=["yaml_parser", "docker_compose_reader", "file_parser"],
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
                    "file_path": "/home/user/project/docker-compose.yml",
                    "version": "3.8",
                    "project_name": "my-project",
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "source_timestamp": "2024-01-10T08:00:00Z",
                    "extraction_tier": "A",
                    "extraction_method": "yaml_parser",
                    "confidence": 1.0,
                    "extractor_version": "1.0.0",
                }
            ]
        }
    }
