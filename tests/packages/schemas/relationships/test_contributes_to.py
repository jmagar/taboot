"""Tests for ContributesToRelationship schema."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.relationships.contributes_to import ContributesToRelationship


class TestContributesToRelationship:
    """Test suite for ContributesToRelationship (Person → Repository)."""

    def test_contributes_to_relationship_minimal_valid(self) -> None:
        """Test ContributesToRelationship with only required fields."""
        now = datetime.now(UTC)
        first_commit = datetime(2020, 1, 1, tzinfo=UTC)
        last_commit = datetime(2024, 1, 15, tzinfo=UTC)

        rel = ContributesToRelationship(
            commit_count=150,
            first_commit_at=first_commit,
            last_commit_at=last_commit,
            created_at=now,
            source="github_reader",
            extractor_version="1.0.0",
        )

        assert rel.commit_count == 150
        assert rel.first_commit_at == first_commit
        assert rel.last_commit_at == last_commit
        assert rel.created_at == now
        assert rel.source == "github_reader"
        assert rel.confidence == 1.0
        assert rel.extractor_version == "1.0.0"

    def test_contributes_to_relationship_full_valid(self) -> None:
        """Test ContributesToRelationship with all fields populated."""
        now = datetime.now(UTC)
        first_commit = datetime(2020, 1, 1, tzinfo=UTC)
        last_commit = datetime(2024, 1, 15, tzinfo=UTC)
        source_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        rel = ContributesToRelationship(
            commit_count=500,
            first_commit_at=first_commit,
            last_commit_at=last_commit,
            created_at=now,
            source_timestamp=source_time,
            source="github_reader",
            confidence=0.98,
            extractor_version="1.2.0",
        )

        assert rel.commit_count == 500
        assert rel.first_commit_at == first_commit
        assert rel.last_commit_at == last_commit
        assert rel.source_timestamp == source_time
        assert rel.confidence == 0.98

    def test_contributes_to_relationship_single_commit(self) -> None:
        """Test ContributesToRelationship with single commit."""
        now = datetime.now(UTC)
        commit_time = datetime(2024, 1, 1, tzinfo=UTC)

        rel = ContributesToRelationship(
            commit_count=1,
            first_commit_at=commit_time,
            last_commit_at=commit_time,
            created_at=now,
            source="github_reader",
            extractor_version="1.0.0",
        )

        assert rel.commit_count == 1
        assert rel.first_commit_at == commit_time
        assert rel.last_commit_at == commit_time

    def test_contributes_to_relationship_large_commit_count(self) -> None:
        """Test ContributesToRelationship with large commit count."""
        now = datetime.now(UTC)
        first_commit = datetime(2015, 1, 1, tzinfo=UTC)
        last_commit = datetime(2024, 12, 31, tzinfo=UTC)

        rel = ContributesToRelationship(
            commit_count=10000,
            first_commit_at=first_commit,
            last_commit_at=last_commit,
            created_at=now,
            source="github_reader",
            extractor_version="1.0.0",
        )

        assert rel.commit_count == 10000

    def test_contributes_to_relationship_missing_required_commit_count(self) -> None:
        """Test ContributesToRelationship validation fails without commit_count."""
        now = datetime.now(UTC)
        first_commit = datetime(2020, 1, 1, tzinfo=UTC)
        last_commit = datetime(2024, 1, 15, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            ContributesToRelationship(
                first_commit_at=first_commit,
                last_commit_at=last_commit,
                created_at=now,
                source="github_reader",
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("commit_count",) for e in errors)

    def test_contributes_to_relationship_invalid_commit_count_zero(self) -> None:
        """Test ContributesToRelationship validation fails with zero commit_count."""
        now = datetime.now(UTC)
        first_commit = datetime(2020, 1, 1, tzinfo=UTC)
        last_commit = datetime(2024, 1, 15, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            ContributesToRelationship(
                commit_count=0,
                first_commit_at=first_commit,
                last_commit_at=last_commit,
                created_at=now,
                source="github_reader",
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("commit_count",) for e in errors)

    def test_contributes_to_relationship_invalid_commit_count_negative(self) -> None:
        """Test ContributesToRelationship validation fails with negative commit_count."""
        now = datetime.now(UTC)
        first_commit = datetime(2020, 1, 1, tzinfo=UTC)
        last_commit = datetime(2024, 1, 15, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            ContributesToRelationship(
                commit_count=-5,
                first_commit_at=first_commit,
                last_commit_at=last_commit,
                created_at=now,
                source="github_reader",
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("commit_count",) for e in errors)

    def test_contributes_to_relationship_missing_required_first_commit_at(self) -> None:
        """Test ContributesToRelationship validation fails without first_commit_at."""
        now = datetime.now(UTC)
        last_commit = datetime(2024, 1, 15, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            ContributesToRelationship(
                commit_count=150,
                last_commit_at=last_commit,
                created_at=now,
                source="github_reader",
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("first_commit_at",) for e in errors)

    def test_contributes_to_relationship_missing_required_last_commit_at(self) -> None:
        """Test ContributesToRelationship validation fails without last_commit_at."""
        now = datetime.now(UTC)
        first_commit = datetime(2020, 1, 1, tzinfo=UTC)

        with pytest.raises(ValidationError) as exc_info:
            ContributesToRelationship(
                commit_count=150,
                first_commit_at=first_commit,
                created_at=now,
                source="github_reader",
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("last_commit_at",) for e in errors)

    def test_contributes_to_relationship_serialization(self) -> None:
        """Test ContributesToRelationship can be serialized to dict."""
        now = datetime.now(UTC)
        first_commit = datetime(2020, 1, 1, tzinfo=UTC)
        last_commit = datetime(2024, 1, 15, tzinfo=UTC)

        rel = ContributesToRelationship(
            commit_count=150,
            first_commit_at=first_commit,
            last_commit_at=last_commit,
            created_at=now,
            source="github_reader",
            extractor_version="1.0.0",
        )

        data = rel.model_dump()
        assert data["commit_count"] == 150
        assert data["first_commit_at"] == first_commit
        assert data["last_commit_at"] == last_commit
        assert data["confidence"] == 1.0
