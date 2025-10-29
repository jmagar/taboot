"""Tests for RoutesToRelationship schema."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.relationships.routes_to import RoutesToRelationship


class TestRoutesToRelationship:
    """Test suite for RoutesToRelationship (Proxy → Service)."""

    def test_routes_to_relationship_minimal_valid(self) -> None:
        """Test RoutesToRelationship with only required fields."""
        now = datetime.now(UTC)

        rel = RoutesToRelationship(
            host="example.com",
            path="/",
            tls=True,
            auth_enabled=False,
            created_at=now,
            updated_at=now,
            source="swag_reader",
            extractor_version="1.0.0",
        )

        assert rel.host == "example.com"
        assert rel.path == "/"
        assert rel.tls is True
        assert rel.auth_enabled is False
        assert rel.created_at == now
        assert rel.updated_at == now
        assert rel.source == "swag_reader"
        assert rel.confidence == 1.0
        assert rel.extractor_version == "1.0.0"

    def test_routes_to_relationship_full_valid(self) -> None:
        """Test RoutesToRelationship with all fields populated."""
        now = datetime.now(UTC)
        source_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        rel = RoutesToRelationship(
            host="api.service.local",
            path="/api/v1",
            tls=True,
            auth_enabled=True,
            created_at=now,
            updated_at=now,
            source_timestamp=source_time,
            source="swag_reader",
            confidence=0.98,
            extractor_version="1.2.0",
        )

        assert rel.host == "api.service.local"
        assert rel.path == "/api/v1"
        assert rel.tls is True
        assert rel.auth_enabled is True
        assert rel.source_timestamp == source_time
        assert rel.confidence == 0.98

    def test_routes_to_relationship_no_tls(self) -> None:
        """Test RoutesToRelationship with TLS disabled."""
        now = datetime.now(UTC)

        rel = RoutesToRelationship(
            host="internal.local",
            path="/health",
            tls=False,
            auth_enabled=False,
            created_at=now,
            updated_at=now,
            source="swag_reader",
            extractor_version="1.0.0",
        )

        assert rel.tls is False
        assert rel.auth_enabled is False

    def test_routes_to_relationship_missing_required_host(self) -> None:
        """Test RoutesToRelationship validation fails without host."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            RoutesToRelationship(
                path="/api",
                tls=True,
                auth_enabled=True,
                created_at=now,
                updated_at=now,
                source="swag_reader",
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("host",) for e in errors)

    def test_routes_to_relationship_missing_required_path(self) -> None:
        """Test RoutesToRelationship validation fails without path."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            RoutesToRelationship(
                host="example.com",
                tls=True,
                auth_enabled=True,
                created_at=now,
                updated_at=now,
                source="swag_reader",
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("path",) for e in errors)

    def test_routes_to_relationship_missing_required_tls(self) -> None:
        """Test RoutesToRelationship validation fails without tls."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            RoutesToRelationship(
                host="example.com",
                path="/api",
                auth_enabled=True,
                created_at=now,
                updated_at=now,
                source="swag_reader",
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("tls",) for e in errors)

    def test_routes_to_relationship_missing_required_auth_enabled(self) -> None:
        """Test RoutesToRelationship validation fails without auth_enabled."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            RoutesToRelationship(
                host="example.com",
                path="/api",
                tls=True,
                created_at=now,
                updated_at=now,
                source="swag_reader",
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("auth_enabled",) for e in errors)

    def test_routes_to_relationship_empty_host(self) -> None:
        """Test RoutesToRelationship validation fails with empty host."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            RoutesToRelationship(
                host="",
                path="/api",
                tls=True,
                auth_enabled=True,
                created_at=now,
                updated_at=now,
                source="swag_reader",
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("host",) for e in errors)

    def test_routes_to_relationship_empty_path(self) -> None:
        """Test RoutesToRelationship validation fails with empty path."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            RoutesToRelationship(
                host="example.com",
                path="",
                tls=True,
                auth_enabled=True,
                created_at=now,
                updated_at=now,
                source="swag_reader",
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("path",) for e in errors)

    def test_routes_to_relationship_serialization(self) -> None:
        """Test RoutesToRelationship can be serialized to dict."""
        now = datetime.now(UTC)

        rel = RoutesToRelationship(
            host="example.com",
            path="/api",
            tls=True,
            auth_enabled=True,
            created_at=now,
            updated_at=now,
            source="swag_reader",
            extractor_version="1.0.0",
        )

        data = rel.model_dump()
        assert data["host"] == "example.com"
        assert data["path"] == "/api"
        assert data["tls"] is True
        assert data["auth_enabled"] is True
        assert data["confidence"] == 1.0
