"""SwagConfigFile entity schema.

Represents the root SWAG nginx configuration file entity.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SwagConfigFile(BaseModel):
    """SwagConfigFile entity representing a parsed SWAG nginx config file.

    This is the root entity for SWAG configuration parsing. Each SWAG config
    file becomes one SwagConfigFile node in the graph.

    Extracted from:
    - SWAG nginx configuration files in /config/nginx/site-confs/

    Examples:
        >>> from datetime import datetime, UTC
        >>> config = SwagConfigFile(
        ...     file_path="/config/nginx/site-confs/myapp.conf",
        ...     version="1.0",
        ...     parsed_at=datetime.now(UTC),
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="nginx_parser",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> config.file_path
        '/config/nginx/site-confs/myapp.conf'
    """

    # Identity fields
    file_path: str = Field(
        ...,
        min_length=1,
        description="Full path to the SWAG nginx config file",
        examples=[
            "/config/nginx/site-confs/default",
            "/config/nginx/site-confs/myapp.conf",
        ],
    )

    # Config metadata (optional)
    version: str | None = Field(
        None,
        description="Config file version if specified",
        examples=["1.0", "2.1"],
    )
    parsed_at: datetime | None = Field(
        None,
        description="When this config file was parsed",
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
                    "file_path": "/config/nginx/site-confs/myapp.conf",
                    "version": "1.0",
                    "parsed_at": "2024-01-15T10:30:00Z",
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
