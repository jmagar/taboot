"""Tests for Milestone entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- State validation
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.github.milestone import Milestone


class TestMilestoneEntity:
    """Test suite for Milestone entity."""

    def test_milestone_minimal_valid(self) -> None:
        """Test Milestone with only required fields."""
        now = datetime.now(UTC)
        milestone = Milestone(
            number=1,
            title="v1.0 Release",
            state="open",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="github_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert milestone.number == 1
        assert milestone.title == "v1.0 Release"
        assert milestone.state == "open"
        assert milestone.due_on is None
        assert milestone.description is None

    def test_milestone_with_due_date(self) -> None:
        """Test Milestone with due date and description."""
        now = datetime.now(UTC)
        due_date = datetime(2024, 12, 31, 0, 0, 0, tzinfo=UTC)

        milestone = Milestone(
            number=1,
            title="v1.0 Release",
            state="open",
            due_on=due_date,
            description="First major release",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="github_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert milestone.due_on == due_date
        assert milestone.description == "First major release"

    def test_milestone_missing_required_number(self) -> None:
        """Test Milestone validation fails without number."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Milestone(
                title="Test Milestone",
                state="open",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="github_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("number",) for e in errors)
