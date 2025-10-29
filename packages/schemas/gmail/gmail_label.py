"""GmailLabel entity schema.

Represents a Gmail label (system or user-defined).
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class GmailLabel(BaseModel):
    """GmailLabel entity representing a Gmail label.

    Extracted from:
    - Gmail API

    Examples:
        >>> from datetime import datetime, UTC
        >>> label = GmailLabel(
        ...     label_id="Label_1",
        ...     name="Important Work",
        ...     type="user",
        ...     color="#ff0000",
        ...     message_count=42,
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="gmail_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> label.label_id
        'Label_1'
    """

    # Identity field
    label_id: str = Field(
        ...,
        min_length=1,
        description="Gmail label ID (system: INBOX, SENT, etc.; user: Label_1, Label_2)",
        examples=["Label_1", "INBOX", "SENT", "IMPORTANT"],
    )

    # Content fields
    name: str = Field(
        ...,
        min_length=1,
        description="Human-readable label name",
        examples=["Work", "Personal", "Important", "INBOX"],
    )

    # Type field
    type: Literal["system", "user"] = Field(
        ...,
        description="Label type: system (built-in) or user (custom)",
    )

    # Metadata fields (optional)
    color: str | None = Field(
        None,
        description="Label color in hex format (user labels only)",
        examples=["#ff0000", "#00ff00", "#0000ff"],
    )
    message_count: int | None = Field(
        None,
        ge=0,
        description="Number of messages with this label",
        examples=[0, 42, 150],
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

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate type is system or user."""
        if v not in ("system", "user"):
            raise ValueError("type must be 'system' or 'user'")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "label_id": "Label_1",
                    "name": "Important Work",
                    "type": "user",
                    "color": "#ff0000",
                    "message_count": 42,
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "source_timestamp": "2024-01-01T00:00:00Z",
                    "extraction_tier": "A",
                    "extraction_method": "gmail_api",
                    "confidence": 1.0,
                    "extractor_version": "1.0.0",
                },
                {
                    "label_id": "INBOX",
                    "name": "INBOX",
                    "type": "system",
                    "message_count": 150,
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
