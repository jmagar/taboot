"""BinaryAsset entity schema.

Represents binary files/assets from a GitHub repository or release.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class BinaryAsset(BaseModel):
    """GitHub binary asset entity.

    Extracted from:
    - GitHub release assets
    - Repository binary files
    - Build artifacts

    Examples:
        >>> from datetime import datetime, UTC
        >>> asset = BinaryAsset(
        ...     file_path="releases/app-v1.0.0.tar.gz",
        ...     size=1024000,
        ...     mime_type="application/gzip",
        ...     download_url="https://github.com/owner/repo/releases/download/v1.0.0/app-v1.0.0.tar.gz",
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="github_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> asset.size
        1024000
    """

    # Identity fields
    file_path: str = Field(
        ...,
        min_length=1,
        description="Path to the binary file",
        examples=["releases/app-v1.0.0.tar.gz", "dist/app.exe", "build/package.zip"],
    )

    # File metadata
    size: int = Field(
        ...,
        ge=0,
        description="File size in bytes",
        examples=[1024000, 5242880, 104857600],
    )

    # MIME type (optional)
    mime_type: str | None = Field(
        None,
        description="MIME type of the binary file",
        examples=["application/gzip", "application/zip", "application/octet-stream", "application/x-executable"],
    )

    # Download URL (optional)
    download_url: str | None = Field(
        None,
        description="URL to download the binary asset",
        examples=["https://github.com/owner/repo/releases/download/v1.0.0/app-v1.0.0.tar.gz"],
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
        examples=["github_api", "file_scanner"],
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

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "file_path": "releases/app-v1.0.0.tar.gz",
                    "size": 1024000,
                    "mime_type": "application/gzip",
                    "download_url": "https://github.com/owner/repo/releases/download/v1.0.0/app-v1.0.0.tar.gz",
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "source_timestamp": "2024-01-15T08:00:00Z",
                    "extraction_tier": "A",
                    "extraction_method": "github_api",
                    "confidence": 1.0,
                    "extractor_version": "1.0.0",
                }
            ]
        }
    }
