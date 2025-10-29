"""Tests for Branch entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- Boolean field handling
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.github.branch import Branch


class TestBranchEntity:
    """Test suite for Branch entity."""

    def test_branch_minimal_valid(self) -> None:
        """Test Branch with only required fields."""
        now = datetime.now(UTC)
        branch = Branch(
            name="main",
            sha="abc123def456",
            ref="refs/heads/main",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="github_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert branch.name == "main"
        assert branch.sha == "abc123def456"
        assert branch.ref == "refs/heads/main"
        assert branch.protected is None

    def test_branch_protected(self) -> None:
        """Test Branch with protected flag."""
        now = datetime.now(UTC)
        branch = Branch(
            name="main",
            protected=True,
            sha="abc123def456",
            ref="refs/heads/main",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="github_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert branch.protected is True

    def test_branch_missing_required_name(self) -> None:
        """Test Branch validation fails without name."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Branch(
                sha="abc123",
                ref="refs/heads/test",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="github_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)
