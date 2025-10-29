"""ComposeService entity schema.

Represents a service definition in a Docker Compose file.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ComposeService(BaseModel):
    """ComposeService entity representing a Docker Compose service.

    Extracted from Docker Compose YAML files.

    Examples:
        >>> from datetime import datetime, UTC
        >>> service = ComposeService(
        ...     name="web",
        ...     image="nginx:alpine",
        ...     restart="unless-stopped",
        ...     cpus=2.0,
        ...     memory="2048m",
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="yaml_parser",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> service.name
        'web'
    """

    # Identity fields
    name: str = Field(
        ...,
        min_length=1,
        description="Service name (key in services block)",
        examples=["web", "api", "db", "redis", "worker"],
    )
    compose_file_path: str = Field(
        ...,
        min_length=1,
        description="Path to the compose file that defined this service",
        examples=["/home/user/project/docker-compose.yml", "./compose.yaml"],
    )

    # Container configuration (optional)
    image: str | None = Field(
        None,
        description="Docker image to use",
        examples=["nginx:alpine", "postgres:14", "redis:7"],
    )
    command: str | None = Field(
        None,
        description="Command to override default CMD",
        examples=["npm start", "python manage.py runserver", "nginx -g 'daemon off;'"],
    )
    entrypoint: str | None = Field(
        None,
        description="Entrypoint to override default ENTRYPOINT",
        examples=["/docker-entrypoint.sh", "python"],
    )
    restart: str | None = Field(
        None,
        description="Restart policy",
        examples=["always", "unless-stopped", "on-failure", "no"],
    )

    # Resource limits (optional)
    cpus: float | None = Field(
        None,
        ge=0.0,
        description="CPU limit (number of CPUs)",
        examples=[0.5, 1.0, 2.0],
    )
    memory: str | None = Field(
        None,
        description="Memory limit",
        examples=["512m", "1g", "2048m"],
    )

    # User and directory (optional)
    user: str | None = Field(
        None,
        description="User to run as (UID:GID or username)",
        examples=["1000:1000", "nginx", "www-data"],
    )
    working_dir: str | None = Field(
        None,
        description="Working directory inside container",
        examples=["/app", "/var/www", "/usr/src/app"],
    )
    hostname: str | None = Field(
        None,
        description="Container hostname",
        examples=["api.local", "web-01", "db-master"],
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
                    "name": "web",
                    "image": "nginx:alpine",
                    "command": "nginx -g 'daemon off;'",
                    "restart": "unless-stopped",
                    "cpus": 2.0,
                    "memory": "2048m",
                    "user": "nginx",
                    "working_dir": "/app",
                    "hostname": "web.local",
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
