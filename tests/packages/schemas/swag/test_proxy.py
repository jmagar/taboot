"""Tests for Proxy entity schema.

Test coverage:
- Required field validation
- Optional field handling
- Temporal tracking fields
- Confidence validation (0.0-1.0 range)
- Extraction tier validation
- Proxy type validation
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.schemas.swag.proxy import Proxy


class TestProxyEntity:
    """Test suite for Proxy entity."""

    def test_proxy_minimal_valid(self) -> None:
        """Test Proxy with only required fields."""
        now = datetime.now(UTC)
        proxy = Proxy(
            name="myapp-proxy",
            proxy_type="nginx",
            config_path="/config/nginx/site-confs/myapp.conf",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="nginx_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        assert proxy.name == "myapp-proxy"
        assert proxy.proxy_type == "nginx"
        assert proxy.config_path == "/config/nginx/site-confs/myapp.conf"
        assert proxy.created_at == now
        assert proxy.updated_at == now
        assert proxy.extraction_tier == "A"
        assert proxy.extraction_method == "nginx_parser"
        assert proxy.confidence == 1.0
        assert proxy.extractor_version == "1.0.0"
        assert proxy.source_timestamp is None

    def test_proxy_full_valid(self) -> None:
        """Test Proxy with all fields populated."""
        now = datetime.now(UTC)
        source_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

        proxy = Proxy(
            name="production-proxy",
            proxy_type="swag",
            config_path="/config/nginx/site-confs/prod.conf",
            created_at=now,
            updated_at=now,
            source_timestamp=source_time,
            extraction_tier="A",
            extraction_method="nginx_parser",
            confidence=1.0,
            extractor_version="2.0.0",
        )

        assert proxy.name == "production-proxy"
        assert proxy.proxy_type == "swag"
        assert proxy.config_path == "/config/nginx/site-confs/prod.conf"
        assert proxy.source_timestamp == source_time
        assert proxy.extraction_tier == "A"
        assert proxy.confidence == 1.0

    def test_proxy_missing_required_name(self) -> None:
        """Test Proxy validation fails without name."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Proxy(
                proxy_type="nginx",
                config_path="/config/nginx/site-confs/default",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="nginx_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_proxy_empty_name(self) -> None:
        """Test Proxy validation fails with empty name."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Proxy(
                name="",
                proxy_type="nginx",
                config_path="/config/nginx/site-confs/default",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="nginx_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_proxy_missing_required_proxy_type(self) -> None:
        """Test Proxy validation fails without proxy_type."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Proxy(
                name="test-proxy",
                config_path="/config/nginx/site-confs/default",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="nginx_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("proxy_type",) for e in errors)

    def test_proxy_missing_required_config_path(self) -> None:
        """Test Proxy validation fails without config_path."""
        now = datetime.now(UTC)

        with pytest.raises(ValidationError) as exc_info:
            Proxy(
                name="test-proxy",
                proxy_type="nginx",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="nginx_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("config_path",) for e in errors)

    def test_proxy_confidence_validation(self) -> None:
        """Test confidence validation."""
        now = datetime.now(UTC)

        # Below zero
        with pytest.raises(ValidationError) as exc_info:
            Proxy(
                name="test-proxy",
                proxy_type="nginx",
                config_path="/config/nginx/site-confs/default",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="nginx_parser",
                confidence=-0.1,
                extractor_version="1.0.0",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

        # Above one
        with pytest.raises(ValidationError) as exc_info:
            Proxy(
                name="test-proxy",
                proxy_type="nginx",
                config_path="/config/nginx/site-confs/default",
                created_at=now,
                updated_at=now,
                extraction_tier="A",
                extraction_method="nginx_parser",
                confidence=1.1,
                extractor_version="1.0.0",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence",) for e in errors)

    def test_proxy_extraction_tier_validation(self) -> None:
        """Test extraction_tier must be A, B, or C."""
        now = datetime.now(UTC)

        # Valid tiers
        for tier in ["A", "B", "C"]:
            proxy = Proxy(
                name="test-proxy",
                proxy_type="nginx",
                config_path="/config/nginx/site-confs/default",
                created_at=now,
                updated_at=now,
                extraction_tier=tier,
                extraction_method="nginx_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            )
            assert proxy.extraction_tier == tier

        # Invalid tier
        with pytest.raises(ValidationError) as exc_info:
            Proxy(
                name="test-proxy",
                proxy_type="nginx",
                config_path="/config/nginx/site-confs/default",
                created_at=now,
                updated_at=now,
                extraction_tier="D",
                extraction_method="nginx_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("extraction_tier",) for e in errors)

    def test_proxy_serialization(self) -> None:
        """Test Proxy can be serialized to dict."""
        now = datetime.now(UTC)
        proxy = Proxy(
            name="test-proxy",
            proxy_type="swag",
            config_path="/config/nginx/site-confs/test.conf",
            created_at=now,
            updated_at=now,
            extraction_tier="A",
            extraction_method="nginx_parser",
            confidence=1.0,
            extractor_version="1.0.0",
        )

        data = proxy.model_dump()
        assert data["name"] == "test-proxy"
        assert data["proxy_type"] == "swag"
        assert data["config_path"] == "/config/nginx/site-confs/test.conf"

    def test_proxy_deserialization(self) -> None:
        """Test Proxy can be deserialized from dict."""
        now = datetime.now(UTC)
        data = {
            "name": "test-proxy",
            "proxy_type": "nginx",
            "config_path": "/config/nginx/site-confs/test.conf",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "extraction_tier": "A",
            "extraction_method": "nginx_parser",
            "confidence": 1.0,
            "extractor_version": "1.0.0",
        }

        proxy = Proxy.model_validate(data)
        assert proxy.name == "test-proxy"
        assert proxy.proxy_type == "nginx"
        assert proxy.config_path == "/config/nginx/site-confs/test.conf"
