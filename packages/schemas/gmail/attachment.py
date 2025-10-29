"""Attachment entity schema.

Represents a file attachment from a Gmail message.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Attachment(BaseModel):
    """Attachment entity representing a Gmail email attachment.

    Extracted from:
    - Gmail API

    Examples:
        >>> from datetime import datetime, UTC
        >>> attachment = Attachment(
        ...     attachment_id="attach_12345",
        ...     filename="report.pdf",
        ...     mime_type="application/pdf",
        ...     size=2048000,
        ...     content_hash="sha256:abc123def456",
        ...     is_inline=False,
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="gmail_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> attachment.attachment_id
        'attach_12345'
    """

    # Identity field
    attachment_id: str = Field(
        ...,
        min_length=1,
        description="Gmail attachment ID",
        examples=["attach_12345", "ANGjdJ8wZ..."],
    )

    # Content fields
    filename: str = Field(
        ...,
        min_length=1,
        description="Original filename of the attachment",
        examples=["report.pdf", "image.png", "document.docx"],
    )
    mime_type: str = Field(
        ...,
        min_length=1,
        description="MIME type of the attachment",
        examples=[
            "application/pdf",
            "image/png",
            "image/jpeg",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
        ],
    )

    # Metadata fields
    size: int = Field(
        ...,
        ge=0,
        description="Size of the attachment in bytes",
        examples=[1024, 1024000, 10485760],
    )
    content_hash: str | None = Field(
        None,
        description="Content hash for deduplication (e.g., sha256:...)",
        examples=["sha256:abc123def456", "md5:xyz789"],
    )
    is_inline: bool = Field(
        default=False,
        description="Whether this attachment is displayed inline in the email body",
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
        examples=["gmail_api", "mbox_parser", "regex"],
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
                    "attachment_id": "attach_12345",
                    "filename": "report.pdf",
                    "mime_type": "application/pdf",
                    "size": 2048000,
                    "content_hash": "sha256:abc123def456",
                    "is_inline": False,
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "source_timestamp": "2024-01-15T10:30:00Z",
                    "extraction_tier": "A",
                    "extraction_method": "gmail_api",
                    "confidence": 1.0,
                    "extractor_version": "1.0.0",
                },
                {
                    "attachment_id": "attach_img_001",
                    "filename": "logo.png",
                    "mime_type": "image/png",
                    "size": 50000,
                    "is_inline": True,
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "extraction_tier": "A",
                    "extraction_method": "gmail_api",
                    "confidence": 1.0,
                    "extractor_version": "1.0.0",
                },
            ]
        }
    }
