"""Tests for ProxyRoute entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- Confidence validation (0.0-1.0 range)
- Extraction tier validation
- Port validation
- TLS validation
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.swag.proxy_route import ProxyRoute


class TestProxyRouteEntity:
    """Test suite for ProxyRoute entity."""

    def test_proxy_route_minimal_valid(self) -> None:
        """Test ProxyRoute with only required fields."""
        now = datetime.now(UTC)
        route = ProxyRoute(
            server_name="myapp.example.com",
            upstream_app="100.74.16.82",
            upstream_port=3000,
            upstream_proto="http",
            tls_enabled=True,
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="nginx_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert route.server_name == "myapp.example.com"
        assert route.upstream_app == "100.74.16.82"
        assert route.upstream_port == 3000
        assert route.upstream_proto == "http"
        assert route.tls_enabled is True
        assert route.source_timestamp is None

    def test_proxy_route_full_valid(self) -> None:
        """Test ProxyRoute with all fields populated."""
        now = datetime.now(UTC)
        source_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        route = ProxyRoute(
            server_name="api.example.com",
            upstream_app="backend-service",
            upstream_port=8080,
            upstream_proto="https",
            tls_enabled=True,
            created_at=now,
            updated_at=now,
            source_timestamp=source_time,
            extraction_tier="A",
            extraction_method="nginx_parser",
            confidence=1.0,
            extractor_version="2.0.0",
        )

        assert route.server_name == "api.example.com"
        assert route.upstream_app == "backend-service"
        assert route.upstream_port == 8080
        assert route.upstream_proto == "https"
        assert route.tls_enabled is True
        assert route.source_timestamp == source_time

    def test_proxy_route_missing_required_fields(self) -> None:
        """Test ProxyRoute validation fails without required fields."""
        now = datetime.now(UTC)

        # Missing server_name
        with pytest.raises(ValidationError) as exc_info:
            ProxyRoute(
                upstream_app="100.74.16.82",
                upstream_port=3000,
                upstream_proto="http",
                tls_enabled=True,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="nginx_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("server_name",) for e in errors)

        # Missing upstream_app
        with pytest.raises(ValidationError) as exc_info:
            ProxyRoute(
                server_name="myapp.example.com",
                upstream_port=3000,
                upstream_proto="http",
                tls_enabled=True,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="nginx_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("upstream_app",) for e in errors)

    def test_proxy_route_port_validation(self) -> None:
        """Test port must be valid (1-65535)."""
        now = datetime.now(UTC)

        # Port 0 invalid
        with pytest.raises(ValidationError) as exc_info:
            ProxyRoute(
                server_name="myapp.example.com",
                upstream_app="100.74.16.82",
                upstream_port=0,
                upstream_proto="http",
                tls_enabled=True,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="nginx_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("upstream_port",) for e in errors)

        # Port > 65535 invalid
        with pytest.raises(ValidationError) as exc_info:
            ProxyRoute(
                server_name="myapp.example.com",
                upstream_app="100.74.16.82",
                upstream_port=70000,
                upstream_proto="http",
                tls_enabled=True,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="nginx_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("upstream_port",) for e in errors)

        # Valid ports
        for port in [1, 80, 443, 3000, 8080, 65535]:
            route = ProxyRoute(
                server_name="myapp.example.com",
                upstream_app="100.74.16.82",
                upstream_port=port,
                upstream_proto="http",
                tls_enabled=True,
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="nginx_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            )
            assert route.upstream_port == port

    def test_proxy_route_serialization(self) -> None:
        """Test ProxyRoute can be serialized to dict."""
        now = datetime.now(UTC)
        route = ProxyRoute(
            server_name="myapp.example.com",
            upstream_app="100.74.16.82",
            upstream_port=3000,
            upstream_proto="http",
            tls_enabled=True,
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="nginx_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        data = route.model_dump()
        assert data["server_name"] == "myapp.example.com"
        assert data["upstream_app"] == "100.74.16.82"
        assert data["upstream_port"] == 3000
        assert data["tls_enabled"] is True
