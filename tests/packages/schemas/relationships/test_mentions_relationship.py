"""Tests for MentionsRelationship schema."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from packages.schemas.relationships.mentions import MentionsRelationship


class TestMentionsRelationship:
    """Test suite for MentionsRelationship (Document → Entity)."""

    def test_mentions_relationship_minimal_valid(self) -> None:
        """Test MentionsRelationship with only required fields."""
        now = datetime.now(UTC)
        chunk_id = uuid4()

        rel = MentionsRelationship(
            span="John Doe works at Acme Corp",
            section="Introduction",
            chunk_id=chunk_id,
            created_at=now,
            updated_at=now,
            source="job_12345",
            extractor_version="1.0.0",
        )

        assert rel.span == "John Doe works at Acme Corp"
        assert rel.section == "Introduction"
        assert rel.chunk_id == chunk_id
        assert rel.created_at == now
        assert rel.updated_at == now
        assert rel.source == "job_12345"
        assert rel.confidence == 1.0
        assert rel.extractor_version == "1.0.0"

    def test_mentions_relationship_full_valid(self) -> None:
        """Test MentionsRelationship with all fields populated."""
        now = datetime.now(UTC)
        source_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        chunk_id = uuid4()

        rel = MentionsRelationship(
            span="Jane Smith from TechCorp",
            section="Contributors",
            chunk_id=chunk_id,
            created_at=now,
            updated_at=now,
            source_timestamp=source_time,
            source="github_reader",
            confidence=0.95,
            extractor_version="1.2.0",
        )

        assert rel.span == "Jane Smith from TechCorp"
        assert rel.section == "Contributors"
        assert rel.chunk_id == chunk_id
        assert rel.source_timestamp == source_time
        assert rel.confidence == 0.95

    def test_mentions_relationship_missing_required_span(self) -> None:
        """Test MentionsRelationship validation fails without span."""
        now = datetime.now(UTC)
        chunk_id = uuid4()

        with pytest.raises(ValidationError) as exc_info:
            MentionsRelationship(
                section="Introduction",
                chunk_id=chunk_id,
                created_at=now,
                updated_at=now,
                source="job_12345",
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("span",) for e in errors)

    def test_mentions_relationship_missing_required_section(self) -> None:
        """Test MentionsRelationship validation fails without section."""
        now = datetime.now(UTC)
        chunk_id = uuid4()

        with pytest.raises(ValidationError) as exc_info:
            MentionsRelationship(
                span="Test text",
                chunk_id=chunk_id,
                created_at=now,
                updated_at=now,
                source="job_12345",
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("section",) for e in errors)

    def test_mentions_relationship_missing_required_chunk_id(self) -> None:
        """Test MentionsRelationship validation fails without chunk_id."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            MentionsRelationship(
                span="Test text",
                section="Introduction",
                created_at=now,
                updated_at=now,
                source="job_12345",
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("chunk_id",) for e in errors)

    def test_mentions_relationship_serialization(self) -> None:
        """Test MentionsRelationship can be serialized to dict."""
        now = datetime.now(UTC)
        chunk_id = uuid4()

        rel = MentionsRelationship(
            span="Test text",
            section="Body",
            chunk_id=chunk_id,
            created_at=now,
            updated_at=now,
            source="job_12345",
            extractor_version="1.0.0",
        )

        data = rel.model_dump()
        assert data["span"] == "Test text"
        assert data["section"] == "Body"
        assert data["chunk_id"] == chunk_id
        assert data["confidence"] == 1.0
