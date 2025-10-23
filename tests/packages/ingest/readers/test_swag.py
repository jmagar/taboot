"""Tests for SWAG reverse proxy config parser.

Tests nginx config parsing for SWAG proxy configurations.
Following TDD methodology (RED-GREEN-REFACTOR).
"""

import pytest
from datetime import datetime, timezone


class TestSwagReader:
    """Tests for the SwagReader class."""

    def test_parse_basic_proxy_config(self) -> None:
        """Test parsing a basic nginx proxy config with server and location blocks."""
        from packages.ingest.readers.swag import SwagReader

        config = """
        server {
            listen 443 ssl;
            server_name api.example.com;

            location / {
                proxy_pass http://api-service:8080;
            }
        }
        """

        reader = SwagReader()
        result = reader.parse_config(config)

        # Should extract one Proxy node
        assert len(result["proxies"]) == 1
        proxy = result["proxies"][0]
        assert proxy.name == "swag"
        assert proxy.proxy_type.value == "swag"

        # Should extract one ROUTES_TO relationship
        assert len(result["routes"]) == 1
        route = result["routes"][0]
        assert route["host"] == "api.example.com"
        assert route["path"] == "/"
        assert route["target_service"] == "api-service"
        assert route["tls"] is True

    def test_parse_multiple_server_blocks(self) -> None:
        """Test parsing config with multiple server blocks."""
        from packages.ingest.readers.swag import SwagReader

        config = """
        server {
            listen 443 ssl;
            server_name api.example.com;

            location /api/v1 {
                proxy_pass http://api-service:8080;
            }
        }

        server {
            listen 80;
            server_name web.example.com;

            location / {
                proxy_pass http://web-service:3000;
            }
        }
        """

        reader = SwagReader()
        result = reader.parse_config(config)

        # Should extract routes for both servers
        assert len(result["routes"]) == 2

        # First route (SSL)
        route1 = result["routes"][0]
        assert route1["host"] == "api.example.com"
        assert route1["path"] == "/api/v1"
        assert route1["target_service"] == "api-service"
        assert route1["tls"] is True

        # Second route (no SSL)
        route2 = result["routes"][1]
        assert route2["host"] == "web.example.com"
        assert route2["path"] == "/"
        assert route2["target_service"] == "web-service"
        assert route2["tls"] is False

    def test_parse_multiple_locations_same_server(self) -> None:
        """Test parsing multiple location blocks in the same server."""
        from packages.ingest.readers.swag import SwagReader

        config = """
        server {
            listen 443 ssl;
            server_name app.example.com;

            location /api {
                proxy_pass http://api-service:8080;
            }

            location /auth {
                proxy_pass http://auth-service:9000;
            }
        }
        """

        reader = SwagReader()
        result = reader.parse_config(config)

        # Should extract routes for both locations
        assert len(result["routes"]) == 2

        route1 = result["routes"][0]
        assert route1["host"] == "app.example.com"
        assert route1["path"] == "/api"
        assert route1["target_service"] == "api-service"

        route2 = result["routes"][1]
        assert route2["host"] == "app.example.com"
        assert route2["path"] == "/auth"
        assert route2["target_service"] == "auth-service"

    def test_extract_service_from_proxy_pass(self) -> None:
        """Test extracting service name from various proxy_pass formats."""
        from packages.ingest.readers.swag import SwagReader

        reader = SwagReader()

        # Test various proxy_pass formats
        assert reader._extract_service_name("http://api-service:8080") == "api-service"
        assert reader._extract_service_name("http://api-service:8080/") == "api-service"
        assert reader._extract_service_name("http://api-service") == "api-service"
        assert reader._extract_service_name("https://api-service:443") == "api-service"
        assert reader._extract_service_name("http://10.0.0.5:8080") == "10.0.0.5"
        assert reader._extract_service_name("http://localhost:3000") == "localhost"

    def test_parse_empty_config(self) -> None:
        """Test parsing empty config returns empty results."""
        from packages.ingest.readers.swag import SwagReader

        reader = SwagReader()
        result = reader.parse_config("")

        assert len(result["proxies"]) == 1  # Default proxy node
        assert len(result["routes"]) == 0

    def test_parse_config_without_proxy_pass(self) -> None:
        """Test parsing config without proxy_pass directives."""
        from packages.ingest.readers.swag import SwagReader

        config = """
        server {
            listen 443 ssl;
            server_name static.example.com;

            location / {
                root /var/www/html;
            }
        }
        """

        reader = SwagReader()
        result = reader.parse_config(config)

        # Should have proxy node but no routes
        assert len(result["proxies"]) == 1
        assert len(result["routes"]) == 0

    def test_parse_invalid_config_raises_error(self) -> None:
        """Test that invalid nginx syntax raises appropriate error."""
        from packages.ingest.readers.swag import SwagReader, SwagReaderError

        config = """
        server {
            this is not valid nginx syntax
        """

        reader = SwagReader()
        with pytest.raises(SwagReaderError):
            reader.parse_config(config)

    def test_parse_config_with_upstream(self) -> None:
        """Test parsing config with upstream blocks."""
        from packages.ingest.readers.swag import SwagReader

        config = """
        upstream backend {
            server backend-1:8080;
            server backend-2:8080;
        }

        server {
            listen 443 ssl;
            server_name api.example.com;

            location / {
                proxy_pass http://backend;
            }
        }
        """

        reader = SwagReader()
        result = reader.parse_config(config)

        # Should extract route with upstream name
        assert len(result["routes"]) == 1
        route = result["routes"][0]
        assert route["target_service"] == "backend"
        assert route["host"] == "api.example.com"
        assert route["tls"] is True

    def test_parse_config_detects_ssl_variants(self) -> None:
        """Test that SSL detection works for various listen directive formats."""
        from packages.ingest.readers.swag import SwagReader

        config = """
        server {
            listen 443 ssl http2;
            server_name test1.example.com;
            location / { proxy_pass http://svc1:80; }
        }

        server {
            listen 8443 ssl;
            server_name test2.example.com;
            location / { proxy_pass http://svc2:80; }
        }

        server {
            listen 80;
            server_name test3.example.com;
            location / { proxy_pass http://svc3:80; }
        }
        """

        reader = SwagReader()
        result = reader.parse_config(config)

        assert len(result["routes"]) == 3
        assert result["routes"][0]["tls"] is True  # 443 ssl
        assert result["routes"][1]["tls"] is True  # 8443 ssl
        assert result["routes"][2]["tls"] is False  # 80 (no ssl)

    def test_proxy_node_has_required_fields(self) -> None:
        """Test that generated Proxy nodes have all required fields."""
        from packages.ingest.readers.swag import SwagReader

        config = """
        server {
            listen 443 ssl;
            server_name api.example.com;
            location / { proxy_pass http://api:8080; }
        }
        """

        reader = SwagReader()
        result = reader.parse_config(config)

        proxy = result["proxies"][0]

        # Check required fields per data-model.md
        assert proxy.name is not None
        assert proxy.proxy_type is not None
        assert isinstance(proxy.created_at, datetime)
        assert isinstance(proxy.updated_at, datetime)
        assert proxy.metadata is not None or proxy.metadata is None  # Optional field

    def test_route_has_required_fields(self) -> None:
        """Test that generated routes have all required fields."""
        from packages.ingest.readers.swag import SwagReader

        config = """
        server {
            listen 443 ssl;
            server_name api.example.com;
            location /api {
                proxy_pass http://api-service:8080;
            }
        }
        """

        reader = SwagReader()
        result = reader.parse_config(config)

        route = result["routes"][0]

        # Check required fields per data-model.md ROUTES_TO relationship
        assert route["host"] is not None
        assert route["path"] is not None
        assert route["tls"] is not None
        assert isinstance(route["tls"], bool)
        assert route["target_service"] is not None

    def test_parse_config_handles_regex_locations(self) -> None:
        """Test parsing location blocks with regex patterns."""
        from packages.ingest.readers.swag import SwagReader

        config = """
        server {
            listen 443 ssl;
            server_name api.example.com;

            location ~ ^/api/v[0-9]+/ {
                proxy_pass http://api-service:8080;
            }
        }
        """

        reader = SwagReader()
        result = reader.parse_config(config)

        # Should extract route with regex pattern preserved
        assert len(result["routes"]) == 1
        route = result["routes"][0]
        assert "/api/" in route["path"] or "^/api/v" in route["path"]
        assert route["target_service"] == "api-service"

    def test_parse_file(self) -> None:
        """Test parsing config from file path."""
        from packages.ingest.readers.swag import SwagReader
        import tempfile
        import os

        config = """
        server {
            listen 443 ssl;
            server_name file-test.example.com;
            location / { proxy_pass http://test-service:8080; }
        }
        """

        # Write config to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write(config)
            temp_path = f.name

        try:
            reader = SwagReader()
            result = reader.parse_file(temp_path)

            assert len(result["routes"]) == 1
            route = result["routes"][0]
            assert route["host"] == "file-test.example.com"
            assert route["target_service"] == "test-service"
        finally:
            os.unlink(temp_path)

    def test_parse_file_not_found_raises_error(self) -> None:
        """Test that parsing non-existent file raises appropriate error."""
        from packages.ingest.readers.swag import SwagReader, SwagReaderError

        reader = SwagReader()
        with pytest.raises(SwagReaderError):
            reader.parse_file("/nonexistent/path/to/config.conf")
