"""Proxy entity schema.

Represents a proxy configuration entity in SWAG.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Proxy(BaseModel):
    """Proxy entity representing an nginx proxy configuration.

    Each proxy configuration in SWAG becomes one Proxy node in the graph.
    Proxies route traffic from server names to upstream services.

    Extracted from:
    - SWAG nginx server blocks

    Examples:
        >>> from datetime import datetime, UTC
        >>> proxy = Proxy(
        ...     name="myapp-proxy",
        ...     proxy_type="swag",
        ...     config_path="/config/nginx/site-confs/myapp.conf",
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="nginx_parser",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> proxy.name
        'myapp-proxy'
    """

    # Identity fields
    name: str = Field(
        ...,
        min_length=1,
        description="Unique name for this proxy configuration",
        examples=["myapp-proxy", "production-proxy", "api-gateway"],
    )
    proxy_type: str = Field(
        ...,
        description="Type of proxy (nginx, swag, etc.)",
        examples=["nginx", "swag", "traefik"],
    )
    config_path: str = Field(
        ...,
        description="Path to the configuration file defining this proxy",
        examples=[
            "/config/nginx/site-confs/myapp.conf",
            "/config/nginx/site-confs/default",
        ],
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
        examples=["nginx_parser", "regex", "manual_parse"],
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
                    "name": "myapp-proxy",
                    "proxy_type": "swag",
                    "config_path": "/config/nginx/site-confs/myapp.conf",
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
