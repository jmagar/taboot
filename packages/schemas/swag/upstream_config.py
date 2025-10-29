"""UpstreamConfig entity schema.

Represents upstream service configuration in SWAG nginx.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class UpstreamConfig(BaseModel):
    """UpstreamConfig entity representing nginx upstream variables.

    Each UpstreamConfig captures the upstream service configuration extracted
    from nginx variables (set $upstream_app, $upstream_port, $upstream_proto).

    Extracted from:
    - SWAG nginx upstream variable declarations

    Examples:
        >>> from datetime import datetime, UTC
        >>> config = UpstreamConfig(
        ...     app="100.74.16.82",
        ...     port=3000,
        ...     proto="http",
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="nginx_parser",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> config.app
        '100.74.16.82'
    """

    # Upstream fields
    app: str = Field(
        ...,
        min_length=1,
        description="Upstream application IP address or hostname",
        examples=["100.74.16.82", "backend-service", "localhost"],
    )
    port: int = Field(
        ...,
        ge=1,
        le=65535,
        description="Upstream application port",
        examples=[3000, 8080, 443, 80],
    )
    proto: str = Field(
        ...,
        description="Upstream protocol (http or https)",
        examples=["http", "https"],
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
        examples=["nginx_parser", "regex"],
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
        examples=["1.0.0", "2.0.0"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "app": "100.74.16.82",
                    "port": 3000,
                    "proto": "http",
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "source_timestamp": "2024-01-01T12:00:00Z",
                    "extraction_tier": "A",
                    "extraction_method": "nginx_parser",
                    "confidence": 1.0,
                    "extractor_version": "1.0.0",
                }
            ]
        }
    }
