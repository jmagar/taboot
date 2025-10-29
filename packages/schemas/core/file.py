"""File entity schema.

Represents documents, code, and media files.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class File(BaseModel):
    """File entity representing documents, code, and media files.

    Extracted from:
    - GitHub files
    - Gmail attachments
    - YouTube transcripts
    - Local filesystem

    Examples:
        >>> from datetime import datetime, UTC
        >>> file = File(
        ...     name="README.md",
        ...     file_id="file_12345",
        ...     source="github",
        ...     mime_type="text/markdown",
        ...     size_bytes=1024,
        ...     url="https://github.com/org/repo/blob/main/README.md",
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="github_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> file.name
        'README.md'
    """

    # Identity fields
    name: str = Field(
        ...,
        min_length=1,
        description="File name (including extension)",
        examples=["README.md", "document.pdf", "video.mp4"],
    )
    file_id: str = Field(
        ...,
        min_length=1,
        description="Unique file identifier from source system",
        examples=["file_12345", "attachment_abc", "sha256:abc123"],
    )
    source: str = Field(
        ...,
        min_length=1,
        description="Source system",
        examples=["github", "gmail", "youtube", "filesystem"],
    )

    # File metadata (optional)
    mime_type: str | None = Field(
        None,
        description="MIME type",
        examples=["text/markdown", "application/pdf", "video/mp4"],
    )
    size_bytes: int | None = Field(
        None,
        ge=0,
        description="File size in bytes",
        examples=[1024, 1048576],
    )
    url: str | None = Field(
        None,
        description="URL to access the file",
        examples=["https://github.com/org/repo/blob/main/README.md"],
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
        examples=["github_api", "gmail_api", "filesystem", "regex"],
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
                    "name": "README.md",
                    "file_id": "file_12345",
                    "source": "github",
                    "mime_type": "text/markdown",
                    "size_bytes": 1024,
                    "url": "https://github.com/org/repo/blob/main/README.md",
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "source_timestamp": "2024-01-10T08:00:00Z",
                    "extraction_tier": "A",
                    "extraction_method": "github_api",
                    "confidence": 1.0,
                    "extractor_version": "1.0.0",
                }
            ]
        }
    }
