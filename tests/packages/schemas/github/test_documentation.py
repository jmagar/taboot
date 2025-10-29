"""Tests for Documentation entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- Format validation
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.github.documentation import Documentation


class TestDocumentationEntity:
    """Test suite for Documentation entity."""

    def test_documentation_minimal_valid(self) -> None:
        """Test Documentation with only required fields."""
        now = datetime.now(UTC)
        doc = Documentation(
            file_path="README.md",
            content="# Project Name\n\nWelcome to the project!",
            format="markdown",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="github_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert doc.file_path == "README.md"
        assert doc.content == "# Project Name\n\nWelcome to the project!"
        assert doc.format == "markdown"
        assert doc.title is None

    def test_documentation_with_title(self) -> None:
        """Test Documentation with title."""
        now = datetime.now(UTC)
        doc = Documentation(
            file_path="docs/api.rst",
            content="API Reference\n=============",
            format="rst",
            title="API Reference",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="github_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert doc.format == "rst"
        assert doc.title == "API Reference"

    def test_documentation_missing_required_file_path(self) -> None:
        """Test Documentation validation fails without file_path."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Documentation(
                content="Test content",
                format="markdown",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="github_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("file_path",) for e in errors)
