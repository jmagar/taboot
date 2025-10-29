"""Document entity schema.

Represents a document from Web/Elasticsearch sources.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Document(BaseModel):
    """Document entity representing a web page or Elasticsearch document.

    Extracted from:
    - Firecrawl web scraping
    - Elasticsearch queries
    - Direct web ingestion

    Examples:
        >>> from datetime import datetime, UTC
        >>> doc = Document(
        ...     doc_id="doc_12345",
        ...     source_url="https://example.com/page",
        ...     source_type="web",
        ...     content_hash="abc123def456",
        ...     ingested_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        ...     extraction_state="pending",
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="firecrawl",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> doc.doc_id
        'doc_12345'
    """

    # Identity fields
    doc_id: str = Field(
        ...,
        min_length=1,
        description="Unique document identifier",
        examples=["doc_12345", "es_abc123", "web_https_example_com_page"],
    )
    source_url: str = Field(
        ...,
        min_length=1,
        description="Original URL of the document",
        examples=[
            "https://example.com/page",
            "https://docs.anthropic.com/claude",
            "https://github.com/anthropics/claude-code",
        ],
    )
    source_type: str = Field(
        ...,
        min_length=1,
        description="Source system type",
        examples=["web", "elasticsearch", "firecrawl", "direct"],
    )

    # Content metadata
    content_hash: str = Field(
        ...,
        min_length=1,
        description="Hash of document content for deduplication and change detection",
        examples=["abc123def456", "sha256:a1b2c3d4e5f6", "md5:1234567890abcdef"],
    )

    # Ingestion metadata
    ingested_at: datetime = Field(
        ...,
        description="When the document was ingested into the system",
    )
    extraction_state: Literal["pending", "processing", "completed", "failed"] = Field(
        ...,
        description="Current state of entity extraction for this document",
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
        examples=["firecrawl", "elasticsearch_api", "web_scraper", "playwright"],
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

    @field_validator("extraction_state")
    @classmethod
    def validate_extraction_state(cls, v: str) -> str:
        """Validate extraction_state is pending, processing, completed, or failed."""
        if v not in ("pending", "processing", "completed", "failed"):
            raise ValueError(
                "extraction_state must be pending, processing, completed, or failed"
            )
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "doc_id": "doc_12345",
                    "source_url": "https://docs.anthropic.com/claude",
                    "source_type": "web",
                    "content_hash": "sha256:abc123def456789",
                    "ingested_at": "2024-01-15T10:30:00Z",
                    "extraction_state": "completed",
                    "created_at": "2024-01-15T10:30:05Z",
                    "updated_at": "2024-01-15T10:35:00Z",
                    "source_timestamp": "2024-01-15T10:00:00Z",
                    "extraction_tier": "A",
                    "extraction_method": "firecrawl",
                    "confidence": 1.0,
                    "extractor_version": "1.0.0",
                }
            ]
        }
    }
