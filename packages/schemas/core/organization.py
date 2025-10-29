"""Organization entity schema.

Represents companies, teams, and groups across all data sources.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Organization(BaseModel):
    """Organization entity representing companies, teams, and groups.

    Extracted from:
    - GitHub organizations
    - Gmail domains
    - Subreddit communities
    - YouTube channels

    Examples:
        >>> from datetime import datetime, UTC
        >>> org = Organization(
        ...     name="Acme Corp",
        ...     industry="Technology",
        ...     size="100-500",
        ...     website="https://acme.com",
        ...     description="Leading tech company",
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="github_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> org.name
        'Acme Corp'
    """

    # Identity fields
    name: str = Field(
        ...,
        min_length=1,
        description="Organization name",
        examples=["Acme Corp", "Tech Innovations Inc"],
    )

    # Profile fields (optional)
    industry: str | None = Field(
        None,
        description="Industry or sector",
        examples=["Technology", "Healthcare", "Finance"],
    )
    size: str | None = Field(
        None,
        description="Organization size",
        examples=["1-10", "11-50", "51-200", "201-500", "500+"],
    )
    website: str | None = Field(
        None,
        description="Organization website URL",
        examples=["https://acme.com"],
    )
    description: str | None = Field(
        None,
        description="Organization description or bio",
        examples=["Leading technology company focused on AI"],
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
        examples=["github_api", "spacy_ner", "qwen3_llm", "regex"],
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
                    "name": "Acme Corp",
                    "industry": "Technology",
                    "size": "100-500",
                    "website": "https://acme.com",
                    "description": "Leading technology company",
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "source_timestamp": "2020-05-10T08:00:00Z",
                    "extraction_tier": "A",
                    "extraction_method": "github_api",
                    "confidence": 1.0,
                    "extractor_version": "1.0.0",
                }
            ]
        }
    }
