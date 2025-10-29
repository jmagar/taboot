"""ProxyRoute entity schema.

Represents a routing rule in SWAG nginx configuration.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ProxyRoute(BaseModel):
    """ProxyRoute entity representing an nginx routing rule.

    Each ProxyRoute defines how traffic for a specific server_name is routed
    to an upstream service (IP/hostname + port + protocol).

    Extracted from:
    - SWAG nginx server blocks with upstream variables

    Examples:
        >>> from datetime import datetime, UTC
        >>> route = ProxyRoute(
        ...     server_name="myapp.example.com",
        ...     upstream_app="100.74.16.82",
        ...     upstream_port=3000,
        ...     upstream_proto="http",
        ...     tls_enabled=True,
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="nginx_parser",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> route.server_name
        'myapp.example.com'
    """

    # Routing fields
    server_name: str = Field(
        ...,
        min_length=1,
        description="Server name (hostname) for this route",
        examples=["myapp.example.com", "api.example.com", "*.example.com"],
    )
    upstream_app: str = Field(
        ...,
        description="Upstream application IP address or hostname",
        examples=["100.74.16.82", "backend-service", "localhost"],
    )
    upstream_port: int = Field(
        ...,
        ge=1,
        le=65535,
        description="Upstream application port",
        examples=[3000, 8080, 443, 80],
    )
    upstream_proto: str = Field(
        ...,
        description="Upstream protocol (http or https)",
        examples=["http", "https"],
    )
    tls_enabled: bool = Field(
        ...,
        description="Whether TLS/SSL is enabled for this route",
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
                    "server_name": "myapp.example.com",
                    "upstream_app": "100.74.16.82",
                    "upstream_port": 3000,
                    "upstream_proto": "http",
                    "tls_enabled": True,
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
