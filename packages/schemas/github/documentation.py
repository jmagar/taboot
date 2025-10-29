"""Documentation entity schema.

Represents documentation files from a GitHub repository (README, API docs, etc.).
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Documentation(BaseModel):
    """GitHub documentation entity.

    Extracted from:
    - GitHub repository documentation files
    - README files
    - API documentation
    - Wiki pages

    Examples:
        >>> from datetime import datetime, UTC
        >>> doc = Documentation(
        ...     file_path="README.md",
        ...     content="# Project Name\\n\\nWelcome to the project!",
        ...     format="markdown",
        ...     title="Project README",
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="github_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> doc.format
        'markdown'
    """

    # Identity fields
    file_path: str = Field(
        ...,
        min_length=1,
        description="Path to the documentation file in the repository",
        examples=["README.md", "docs/api.rst", "CONTRIBUTING.txt"],
    )

    # Content
    content: str = Field(
        ...,
        min_length=1,
        description="Documentation content",
        examples=["# Project Name\n\nWelcome!", "API Reference\n============="],
    )

    # Format
    format: str = Field(
        ...,
        min_length=1,
        description="Documentation format (markdown, rst, txt, etc.)",
        examples=["markdown", "rst", "txt", "asciidoc"],
    )

    # Title (optional, extracted from content or filename)
    title: str | None = Field(
        None,
        description="Documentation title (extracted from content or filename)",
        examples=["Project README", "API Reference", "Contributing Guide"],
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
        examples=["github_api", "file_reader"],
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
                    "file_path": "README.md",
                    "content": "# Project Name\n\nWelcome to the project!",
                    "format": "markdown",
                    "title": "Project README",
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
