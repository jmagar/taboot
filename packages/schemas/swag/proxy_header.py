"""ProxyHeader entity schema.

Represents HTTP header configuration in SWAG nginx.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ProxyHeader(BaseModel):
    """ProxyHeader entity representing nginx header directives.

    Each ProxyHeader captures an HTTP header directive from nginx configuration
    (add_header or proxy_set_header).

    Extracted from:
    - SWAG nginx add_header and proxy_set_header directives

    Examples:
        >>> from datetime import datetime, UTC
        >>> header = ProxyHeader(
        ...     header_name="X-Frame-Options",
        ...     header_value="SAMEORIGIN",
        ...     header_type="add_header",
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="nginx_parser",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> header.header_name
        'X-Frame-Options'
    """

    # Header fields
    header_name: str = Field(
        ...,
        min_length=1,
        description="HTTP header name",
        examples=["X-Frame-Options", "Host", "X-Forwarded-For", "Content-Security-Policy"],
    )
    header_value: str = Field(
        ...,
        description="HTTP header value",
        examples=["SAMEORIGIN", "$host", "$proxy_add_x_forwarded_for"],
    )
    header_type: str = Field(
        ...,
        description="Type of header directive (add_header or proxy_set_header)",
        examples=["add_header", "proxy_set_header"],
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
                    "header_name": "X-Frame-Options",
                    "header_value": "SAMEORIGIN",
                    "header_type": "add_header",
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
