"""Release entity schema.

Represents a GitHub release with assets and release notes.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Release(BaseModel):
    """GitHub release entity.

    Extracted from:
    - GitHub API release data
    - Release tags
    - Release assets

    Examples:
        >>> from datetime import datetime, UTC
        >>> release = Release(
        ...     tag_name="v1.0.0",
        ...     name="Version 1.0.0",
        ...     body="# What's New\\n\\n- Feature A\\n- Feature B",
        ...     draft=False,
        ...     prerelease=False,
        ...     release_created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        ...     published_at=datetime(2024, 1, 2, 12, 0, 0, tzinfo=UTC),
        ...     tarball_url="https://github.com/owner/repo/archive/v1.0.0.tar.gz",
        ...     zipball_url="https://github.com/owner/repo/archive/v1.0.0.zip",
        ...     created_at=datetime.now(UTC),
        ...     updated_at=datetime.now(UTC),
        ...     extraction_tier="A",
        ...     extraction_method="github_api",
        ...     confidence=1.0,
        ...     extractor_version="1.0.0",
        ... )
        >>> release.tag_name
        'v1.0.0'
    """

    # Identity fields
    tag_name: str = Field(
        ...,
        min_length=1,
        description="Tag name for the release",
        examples=["v1.0.0", "v2.1.3", "release-2024-01"],
    )
    name: str = Field(
        ...,
        min_length=1,
        description="Release name/title",
        examples=["Version 1.0.0", "Major Release", "Hotfix v1.0.1"],
    )

    # Release notes (optional)
    body: str | None = Field(
        None,
        description="Release notes/description (markdown)",
        examples=["# What's New\n\n- Feature A\n- Feature B", "Bug fixes and improvements"],
    )

    # Status flags (optional)
    draft: bool | None = Field(
        None,
        description="Whether the release is a draft",
        examples=[False, True],
    )
    prerelease: bool | None = Field(
        None,
        description="Whether the release is a prerelease/beta",
        examples=[False, True],
    )

    # Release timestamps (separate from our tracking timestamps)
    release_created_at: datetime | None = Field(
        None,
        description="When the release was created on GitHub",
    )
    published_at: datetime | None = Field(
        None,
        description="When the release was published on GitHub",
    )

    # Download URLs (optional)
    tarball_url: str | None = Field(
        None,
        description="URL for tarball download",
        examples=["https://github.com/owner/repo/archive/v1.0.0.tar.gz"],
    )
    zipball_url: str | None = Field(
        None,
        description="URL for zipball download",
        examples=["https://github.com/owner/repo/archive/v1.0.0.zip"],
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
        examples=["github_api", "release_scraper"],
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
                    "tag_name": "v1.0.0",
                    "name": "Version 1.0.0",
                    "body": "# What's New\n\n- Feature A\n- Feature B",
                    "draft": False,
                    "prerelease": False,
                    "release_created_at": "2024-01-01T12:00:00Z",
                    "published_at": "2024-01-02T12:00:00Z",
                    "tarball_url": "https://github.com/owner/repo/archive/v1.0.0.tar.gz",
                    "zipball_url": "https://github.com/owner/repo/archive/v1.0.0.zip",
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "source_timestamp": "2024-01-02T12:00:00Z",
                    "extraction_tier": "A",
                    "extraction_method": "github_api",
                    "confidence": 1.0,
                    "extractor_version": "1.0.0",
                }
            ]
        }
    }
