"""PortBinding entity schema.

Represents a port binding/mapping in a Docker Compose service.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class PortBinding(BaseModel):
    """PortBinding entity representing a Docker port mapping.

    Extracted from Docker Compose service port declarations.

    Examples:
        >>> from datetime import datetime, UTC
        >>> port = PortBinding(
        ...     host_ip="0.0.0.0",
        ...     host_port=8080,
        ...     container_port=80,
        ...     protocol="tcp",
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="yaml_parser",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> port.host_port
        8080
    """

    # Port mapping fields
    compose_file_path: str = Field(
        ...,
        min_length=1,
        description="Path to the compose file that declared this port binding",
        examples=["/home/user/docker-compose.yml", "./compose.yaml"],
    )
    service_name: str = Field(
        ...,
        min_length=1,
        description="Service name this port binding is associated with",
        examples=["web", "api"],
    )
    host_ip: str | None = Field(
        None,
        description="Host IP to bind to (0.0.0.0 = all interfaces)",
        examples=["0.0.0.0", "127.0.0.1", "192.168.1.10"],
    )
    host_port: int | None = Field(
        None,
        ge=1,
        le=65535,
        description="Host port number",
        examples=[8080, 3000, 5432],
    )
    container_port: int = Field(
        ...,
        ge=1,
        le=65535,
        description="Container port number",
        examples=[80, 3000, 5432, 6379],
    )
    protocol: str | None = Field(
        None,
        description="Protocol (tcp or udp)",
        examples=["tcp", "udp"],
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
                    "host_ip": "0.0.0.0",
                    "host_port": 8080,
                    "container_port": 80,
                    "protocol": "tcp",
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
