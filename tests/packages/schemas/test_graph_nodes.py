"""Tests for graph node Pydantic models (Neo4j entities)."""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from packages.schemas.models import (
    Service,
    Host,
    IP,
    Proxy,
    Endpoint,
    IPType,
    IPAllocation,
    ProxyType,
    HttpMethod,
)


class TestService:
    """Test Service node model."""

    def test_valid_service(self) -> None:
        """Test valid Service node."""
        now = datetime.now(timezone.utc)

        service = Service(
            name="api-service",
            description="Main API service",
            image="myapp/api:v1.0.0",
            version="v1.0.0",
            metadata={"env": "production", "replicas": 3},
            created_at=now,
            updated_at=now,
            extraction_version="v1.2.0",
        )

        assert service.name == "api-service"
        assert service.description == "Main API service"
        assert service.image == "myapp/api:v1.0.0"
        assert service.version == "v1.0.0"
        assert service.metadata == {"env": "production", "replicas": 3}
        assert service.extraction_version == "v1.2.0"

    def test_service_name_required(self) -> None:
        """Test that name is required."""
        now = datetime.now(timezone.utc)

        with pytest.raises(ValidationError) as exc_info:
            Service(created_at=now, updated_at=now)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_service_name_max_length(self) -> None:
        """Test that name has max length of 256 chars."""
        now = datetime.now(timezone.utc)

        with pytest.raises(ValidationError) as exc_info:
            Service(name="x" * 257, created_at=now, updated_at=now)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)


class TestHost:
    """Test Host node model."""

    def test_valid_host(self) -> None:
        """Test valid Host node."""
        now = datetime.now(timezone.utc)

        host = Host(
            hostname="server01.example.com",
            ip_addresses=["192.168.1.10", "10.0.0.5"],
            os="Ubuntu 22.04",
            location="us-east-1a",
            metadata={"datacenter": "aws"},
            created_at=now,
            updated_at=now,
            extraction_version="v1.0.0",
        )

        assert host.hostname == "server01.example.com"
        assert host.ip_addresses == ["192.168.1.10", "10.0.0.5"]
        assert host.os == "Ubuntu 22.04"
        assert host.location == "us-east-1a"

    def test_host_hostname_required(self) -> None:
        """Test that hostname is required."""
        now = datetime.now(timezone.utc)

        with pytest.raises(ValidationError) as exc_info:
            Host(created_at=now, updated_at=now)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("hostname",) for e in errors)

    def test_host_hostname_max_length(self) -> None:
        """Test that hostname has max length of 256 chars."""
        now = datetime.now(timezone.utc)

        with pytest.raises(ValidationError) as exc_info:
            Host(hostname="x" * 257, created_at=now, updated_at=now)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("hostname",) for e in errors)


class TestIP:
    """Test IP node model."""

    def test_valid_ipv4(self) -> None:
        """Test valid IPv4 address."""
        now = datetime.now(timezone.utc)

        ip = IP(
            addr="192.168.1.10",
            ip_type=IPType.V4,
            allocation=IPAllocation.STATIC,
            metadata={"gateway": "192.168.1.1"},
            created_at=now,
            updated_at=now,
        )

        assert ip.addr == "192.168.1.10"
        assert ip.ip_type == IPType.V4
        assert ip.allocation == IPAllocation.STATIC

    def test_valid_ipv6(self) -> None:
        """Test valid IPv6 address."""
        now = datetime.now(timezone.utc)

        ip = IP(
            addr="2001:0db8:85a3::8a2e:0370:7334",
            ip_type=IPType.V6,
            allocation=IPAllocation.DHCP,
            created_at=now,
            updated_at=now,
        )

        assert ip.ip_type == IPType.V6
        assert ip.allocation == IPAllocation.DHCP

    def test_valid_cidr(self) -> None:
        """Test valid CIDR notation."""
        now = datetime.now(timezone.utc)

        ip = IP(
            addr="10.0.0.0/24",
            ip_type=IPType.V4,
            allocation=IPAllocation.UNKNOWN,
            created_at=now,
            updated_at=now,
        )

        assert ip.addr == "10.0.0.0/24"

    def test_ip_addr_required(self) -> None:
        """Test that addr is required."""
        now = datetime.now(timezone.utc)

        with pytest.raises(ValidationError) as exc_info:
            IP(ip_type=IPType.V4, allocation=IPAllocation.STATIC, created_at=now, updated_at=now)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("addr",) for e in errors)

    def test_ip_type_required(self) -> None:
        """Test that ip_type is required."""
        now = datetime.now(timezone.utc)

        with pytest.raises(ValidationError) as exc_info:
            IP(addr="192.168.1.10", allocation=IPAllocation.STATIC, created_at=now, updated_at=now)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("ip_type",) for e in errors)


class TestProxy:
    """Test Proxy node model."""

    def test_valid_proxy(self) -> None:
        """Test valid Proxy node."""
        now = datetime.now(timezone.utc)

        proxy = Proxy(
            name="nginx-proxy",
            proxy_type=ProxyType.NGINX,
            config_path="/etc/nginx/nginx.conf",
            metadata={"version": "1.21"},
            created_at=now,
            updated_at=now,
        )

        assert proxy.name == "nginx-proxy"
        assert proxy.proxy_type == ProxyType.NGINX
        assert proxy.config_path == "/etc/nginx/nginx.conf"

    def test_proxy_swag_type(self) -> None:
        """Test SWAG proxy type."""
        now = datetime.now(timezone.utc)

        proxy = Proxy(
            name="swag",
            proxy_type=ProxyType.SWAG,
            created_at=now,
            updated_at=now,
        )

        assert proxy.proxy_type == ProxyType.SWAG

    def test_proxy_name_required(self) -> None:
        """Test that name is required."""
        now = datetime.now(timezone.utc)

        with pytest.raises(ValidationError) as exc_info:
            Proxy(proxy_type=ProxyType.NGINX, created_at=now, updated_at=now)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_proxy_type_required(self) -> None:
        """Test that proxy_type is required."""
        now = datetime.now(timezone.utc)

        with pytest.raises(ValidationError) as exc_info:
            Proxy(name="proxy", created_at=now, updated_at=now)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("proxy_type",) for e in errors)


class TestEndpoint:
    """Test Endpoint node model."""

    def test_valid_endpoint(self) -> None:
        """Test valid Endpoint node."""
        now = datetime.now(timezone.utc)

        endpoint = Endpoint(
            service="api-service",
            method=HttpMethod.GET,
            path="/api/v1/users/{id}",
            auth="JWT",
            rate_limit=1000,
            metadata={"timeout": 30},
            created_at=now,
            updated_at=now,
        )

        assert endpoint.service == "api-service"
        assert endpoint.method == HttpMethod.GET
        assert endpoint.path == "/api/v1/users/{id}"
        assert endpoint.auth == "JWT"
        assert endpoint.rate_limit == 1000

    def test_endpoint_all_methods(self) -> None:
        """Test all HTTP method enums."""
        now = datetime.now(timezone.utc)

        methods = [
            HttpMethod.GET,
            HttpMethod.POST,
            HttpMethod.PUT,
            HttpMethod.PATCH,
            HttpMethod.DELETE,
            HttpMethod.ALL,
        ]

        for method in methods:
            endpoint = Endpoint(
                service="api-service",
                method=method,
                path="/test",
                created_at=now,
                updated_at=now,
            )
            assert endpoint.method == method

    def test_endpoint_service_required(self) -> None:
        """Test that service is required."""
        now = datetime.now(timezone.utc)

        with pytest.raises(ValidationError) as exc_info:
            Endpoint(method=HttpMethod.GET, path="/test", created_at=now, updated_at=now)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("service",) for e in errors)

    def test_endpoint_method_required(self) -> None:
        """Test that method is required."""
        now = datetime.now(timezone.utc)

        with pytest.raises(ValidationError) as exc_info:
            Endpoint(service="api", path="/test", created_at=now, updated_at=now)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("method",) for e in errors)

    def test_endpoint_path_required(self) -> None:
        """Test that path is required."""
        now = datetime.now(timezone.utc)

        with pytest.raises(ValidationError) as exc_info:
            Endpoint(service="api", method=HttpMethod.GET, created_at=now, updated_at=now)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("path",) for e in errors)

    def test_endpoint_path_max_length(self) -> None:
        """Test that path has max length of 512 chars."""
        now = datetime.now(timezone.utc)

        with pytest.raises(ValidationError) as exc_info:
            Endpoint(
                service="api",
                method=HttpMethod.GET,
                path="/" + "x" * 512,
                created_at=now,
                updated_at=now,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("path",) for e in errors)

    def test_endpoint_rate_limit_non_negative(self) -> None:
        """Test that rate_limit must be non-negative."""
        now = datetime.now(timezone.utc)

        with pytest.raises(ValidationError) as exc_info:
            Endpoint(
                service="api",
                method=HttpMethod.GET,
                path="/test",
                rate_limit=-1,
                created_at=now,
                updated_at=now,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("rate_limit",) for e in errors)
