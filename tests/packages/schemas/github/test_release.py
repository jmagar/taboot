"""Tests for Release entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- Boolean field handling
- URL validation
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.github.release import Release


class TestReleaseEntity:
    """Test suite for Release entity."""

    def test_release_minimal_valid(self) -> None:
        """Test Release with only required fields."""
        now = datetime.now(UTC)
        release = Release(
            tag_name="v1.0.0",
            name="Version 1.0.0",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="github_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert release.tag_name == "v1.0.0"
        assert release.name == "Version 1.0.0"
        assert release.body is None
        assert release.draft is None
        assert release.prerelease is None
        assert release.release_created_at is None
        assert release.published_at is None
        assert release.tarball_url is None
        assert release.zipball_url is None

    def test_release_full_valid(self) -> None:
        """Test Release with all fields populated."""
        now = datetime.now(UTC)
        created_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        published_time = datetime(2024, 1, 2, 12, 0, 0, tzinfo=UTC)

        release = Release(
            tag_name="v1.0.0",
            name="Version 1.0.0",
            body="# What's New\n\n- Feature A\n- Feature B",
            draft=False,
            prerelease=False,
            release_created_at=created_time,
            published_at=published_time,
            tarball_url="https://github.com/owner/repo/archive/v1.0.0.tar.gz",
            zipball_url="https://github.com/owner/repo/archive/v1.0.0.zip",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="github_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert release.body == "# What's New\n\n- Feature A\n- Feature B"
        assert release.draft is False
        assert release.prerelease is False
        assert release.release_created_at == created_time
        assert release.published_at == published_time
        assert release.tarball_url == "https://github.com/owner/repo/archive/v1.0.0.tar.gz"

    def test_release_missing_required_tag_name(self) -> None:
        """Test Release validation fails without tag_name."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Release(
                name="Test Release",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="github_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("tag_name",) for e in errors)
