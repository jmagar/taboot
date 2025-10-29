"""DeviceMapping entity schema.

Represents a device mapping for a Docker Compose service.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class DeviceMapping(BaseModel):
    """DeviceMapping entity representing a host-to-container device mapping.

    Extracted from Docker Compose service devices declarations.

    Examples:
        >>> from datetime import datetime, UTC
        >>> device = DeviceMapping(
        ...     host_device="/dev/video0",
        ...     container_device="/dev/video0",
        ...     permissions="rwm",
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="yaml_parser",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> device.host_device
        '/dev/video0'
    """

    # Device mapping fields
    host_device: str = Field(
        ...,
        min_length=1,
        description="Host device path",
        examples=["/dev/sda", "/dev/video0", "/dev/nvidia0", "/dev/ttyUSB0"],
    )
    container_device: str = Field(
        ...,
        min_length=1,
        description="Container device path (where device appears inside container)",
        examples=["/dev/xvda", "/dev/video0", "/dev/nvidia0", "/dev/ttyUSB0"],
    )
    permissions: str | None = Field(
        None,
        description="Device permissions (r=read, w=write, m=mknod)",
        examples=["rwm", "r", "rw", "rm"],
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
                    "host_device": "/dev/video0",
                    "container_device": "/dev/video0",
                    "permissions": "rwm",
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
