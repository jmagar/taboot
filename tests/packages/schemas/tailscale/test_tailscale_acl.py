"""Tests for TailscaleACL entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- Confidence validation (0.0-1.0 range)
- Extraction tier validation
- List fields (source_tags, destination_tags, ports)
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.tailscale.tailscale_acl import TailscaleACL


class TestTailscaleACLEntity:
    """Test suite for TailscaleACL entity."""

    def test_tailscale_acl_minimal_valid(self) -> None:
        """Test TailscaleACL with only required fields."""
        now = datetime.now(UTC)
        acl = TailscaleACL(
            rule_id="acl-rule-123",
            action="accept",
            source_tags=["tag:production"],
            destination_tags=["tag:database"],
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="tailscale_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert acl.rule_id == "acl-rule-123"
        assert acl.action == "accept"
        assert acl.source_tags == ["tag:production"]
        assert acl.destination_tags == ["tag:database"]
        assert acl.created_at == now
        assert acl.updated_at == now
        assert acl.extraction_tier == "A"
        assert acl.extraction_method == "tailscale_api"
        assert acl.confidence == 1.0
        assert acl.extractor_version == "1.0.0"
        assert acl.ports is None
        assert acl.source_timestamp is None

    def test_tailscale_acl_full_valid(self) -> None:
        """Test TailscaleACL with all fields populated."""
        now = datetime.now(UTC)
        source_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        acl = TailscaleACL(
            rule_id="acl-rule-456",
            action="deny",
            source_tags=["tag:staging", "tag:development"],
            destination_tags=["tag:production", "tag:database"],
            ports=["3306", "5432", "6379"],
            created_at=now,
            updated_at=now,
            source_timestamp=source_time,
            extraction_tier="A",
            extraction_method="tailscale_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert acl.rule_id == "acl-rule-456"
        assert acl.action == "deny"
        assert acl.source_tags == ["tag:staging", "tag:development"]
        assert acl.destination_tags == ["tag:production", "tag:database"]
        assert acl.ports == ["3306", "5432", "6379"]
        assert acl.source_timestamp == source_time
        assert acl.extraction_tier == "A"
        assert acl.confidence == 1.0

    def test_tailscale_acl_missing_required_rule_id(self) -> None:
        """Test TailscaleACL validation fails without rule_id."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            TailscaleACL(
                action="accept",
                source_tags=["tag:production"],
                destination_tags=["tag:database"],
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="tailscale_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("rule_id",) for e in errors)

    def test_tailscale_acl_missing_required_action(self) -> None:
        """Test TailscaleACL validation fails without action."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            TailscaleACL(
                rule_id="acl-rule-123",
                source_tags=["tag:production"],
                destination_tags=["tag:database"],
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="tailscale_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("action",) for e in errors)

    def test_tailscale_acl_missing_required_source_tags(self) -> None:
        """Test TailscaleACL validation fails without source_tags."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            TailscaleACL(
                rule_id="acl-rule-123",
                action="accept",
                destination_tags=["tag:database"],
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="tailscale_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("source_tags",) for e in errors)

    def test_tailscale_acl_missing_required_destination_tags(self) -> None:
        """Test TailscaleACL validation fails without destination_tags."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            TailscaleACL(
                rule_id="acl-rule-123",
                action="accept",
                source_tags=["tag:production"],
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="tailscale_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("destination_tags",) for e in errors)

    def test_tailscale_acl_confidence_validation_below_zero(self) -> None:
        """Test confidence must be >= 0.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            TailscaleACL(
                rule_id="acl-rule-123",
                action="accept",
                source_tags=["tag:production"],
                destination_tags=["tag:database"],
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="tailscale_api",
                confidence=-0.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_tailscale_acl_confidence_validation_above_one(self) -> None:
        """Test confidence must be <= 1.0."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            TailscaleACL(
                rule_id="acl-rule-123",
                action="accept",
                source_tags=["tag:production"],
                destination_tags=["tag:database"],
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="tailscale_api",
                confidence=1.1,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_tailscale_acl_extraction_tier_validation(self) -> None:
        """Test extraction_tier must be A, B, or C."""
        now = datetime.now(UTC)

        # Valid tiers
        for tier in ["A", "B", "C"]:
            acl = TailscaleACL(
                rule_id="acl-rule-123",
                action="accept",
                source_tags=["tag:production"],
                destination_tags=["tag:database"],
                created_at=now,
                updated_at=now,
                extraction_tier=tier,
                extraction_method="tailscale_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )
            assert acl.extraction_tier == tier

        # Invalid tier
        with pytest.raises(ValidationError) as exc_info:
            TailscaleACL(
                rule_id="acl-rule-123",
                action="accept",
                source_tags=["tag:production"],
                destination_tags=["tag:database"],
                created_at=now,
                updated_at=now,
                extraction_tier="D",
                extraction_method="tailscale_api",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extraction_tier",) for e in errors)

    def test_tailscale_acl_serialization(self) -> None:
        """Test TailscaleACL can be serialized to dict."""
        now = datetime.now(UTC)
        acl = TailscaleACL(
            rule_id="acl-rule-123",
            action="accept",
            source_tags=["tag:production"],
            destination_tags=["tag:database"],
            ports=["3306"],
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="tailscale_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        data = acl.model_dump()
        assert data["rule_id"] == "acl-rule-123"
        assert data["action"] == "accept"
        assert data["source_tags"] == ["tag:production"]
        assert data["destination_tags"] == ["tag:database"]
        assert data["ports"] == ["3306"]
        assert data["confidence"] == 1.0

    def test_tailscale_acl_deserialization(self) -> None:
        """Test TailscaleACL can be deserialized from dict."""
        now = datetime.now(UTC)
        data = {
            "rule_id": "acl-rule-123",
            "action": "accept",
            "source_tags": ["tag:production"],
            "destination_tags": ["tag:database"],
            "ports": ["3306"],
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "extraction_tier": "A",
            "extraction_method": "tailscale_api",
            "confidence": 1.0,
            "extractor_version": "1.0.0",
        }

        acl = TailscaleACL.model_validate(data)
        assert acl.rule_id == "acl-rule-123"
        assert acl.action == "accept"
        assert acl.source_tags == ["tag:production"]
        assert acl.destination_tags == ["tag:database"]
        assert acl.ports == ["3306"]

    def test_tailscale_acl_empty_tag_lists(self) -> None:
        """Test TailscaleACL handles empty tag lists."""
        now = datetime.now(UTC)
        acl = TailscaleACL(
            rule_id="acl-rule-123",
            action="accept",
            source_tags=[],
            destination_tags=[],
            ports=[],
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="tailscale_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert acl.source_tags == []
        assert acl.destination_tags == []
        assert acl.ports == []

    def test_tailscale_acl_multiple_tags(self) -> None:
        """Test TailscaleACL with multiple source and destination tags."""
        now = datetime.now(UTC)
        acl = TailscaleACL(
            rule_id="acl-rule-123",
            action="accept",
            source_tags=["tag:web", "tag:api", "tag:frontend"],
            destination_tags=["tag:database", "tag:cache", "tag:storage"],
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="tailscale_api",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert len(acl.source_tags) == 3
        assert len(acl.destination_tags) == 3
        assert "tag:web" in acl.source_tags
        assert "tag:database" in acl.destination_tags
