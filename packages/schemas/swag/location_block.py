"""LocationBlock entity schema.

Represents an nginx location block in SWAG configuration.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class LocationBlock(BaseModel):
    """LocationBlock entity representing an nginx location directive.

    Each LocationBlock defines URL path matching rules and associated
    proxy/auth configuration for a specific path pattern.

    Extracted from:
    - SWAG nginx location blocks

    Examples:
        >>> from datetime import datetime, UTC
        >>> location = LocationBlock(
        ...     path="/api",
        ...     proxy_pass_url="http://backend:8080",
        ...     auth_enabled=True,
        ...     auth_type="authelia",
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="nginx_parser",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> location.path
        '/api'
    """

    # Location fields
    path: str = Field(
        ...,
        min_length=1,
        description="URL path pattern for this location block",
        examples=["/", "/api", "/admin", "~ \\.php$"],
    )
    proxy_pass_url: str | None = Field(
        None,
        description="Proxy pass URL if specified",
        examples=["http://backend:8080", "http://100.74.16.82:3000"],
    )
    auth_enabled: bool = Field(
        False,
        description="Whether authentication is enabled for this location",
    )
    auth_type: str | None = Field(
        None,
        description="Type of authentication (authelia, basic, etc.)",
        examples=["authelia", "basic", "oauth"],
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
                    "path": "/api",
                    "proxy_pass_url": "http://backend:8080",
                    "auth_enabled": True,
                    "auth_type": "authelia",
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
