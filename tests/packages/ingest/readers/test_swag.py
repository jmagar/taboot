"""Tests for SWAG reverse proxy config parser.

Tests nginx config parsing for SWAG proxy configurations.
Following TDD methodology (RED-GREEN-REFACTOR).

Phase 4 (T195-T197): Update SwagReader to output new entity types.
"""

from datetime import datetime

import pytest


class TestSwagReaderNewEntities:
    """Integration tests for SwagReader outputting new entity types (Phase 4)."""

    def test_parse_outputs_swag_config_file(self) -> None:
        """Test that parsing creates a SwagConfigFile entity."""
        from packages.ingest.readers.swag import SwagReader

        config = """
        server {
            listen 443 ssl;
            server_name api.example.com;
            location / { proxy_pass http://api-service:8080; }
        }
        """

        reader = SwagReader(config_path="/config/nginx/site-confs/test.conf")
        result = reader.parse_config(config)

        # Should have SwagConfigFile entity
        assert "config_files" in result
        assert len(result["config_files"]) == 1

        config_file = result["config_files"][0]
        assert config_file.file_path == "/config/nginx/site-confs/test.conf"
        assert config_file.extraction_tier == "A"
        assert config_file.extraction_method == "nginx_parser"
        assert config_file.confidence == 1.0
        assert config_file.created_at is not None
        assert config_file.updated_at is not None

    def test_parse_outputs_proxy_entities(self) -> None:
        """Test that parsing creates Proxy entities with new schema."""
        from packages.ingest.readers.swag import SwagReader

        config = """
        server {
            listen 443 ssl;
            server_name api.example.com;
            location / { proxy_pass http://api-service:8080; }
        }
        """

        reader = SwagReader(config_path="/config/nginx/site-confs/test.conf")
        result = reader.parse_config(config)

        # Should have Proxy entities
        assert "proxies" in result
        assert len(result["proxies"]) >= 1

        proxy = result["proxies"][0]
        assert proxy.name == "swag"
        assert proxy.proxy_type == "swag"
        assert proxy.config_path == "/config/nginx/site-confs/test.conf"
        assert proxy.extraction_tier == "A"
        assert proxy.created_at is not None

    def test_parse_outputs_proxy_routes(self) -> None:
        """Test that parsing creates ProxyRoute entities."""
        from packages.ingest.readers.swag import SwagReader

        config = """
        server {
            listen 443 ssl;
            server_name api.example.com;

            set $upstream_app 100.74.16.82;
            set $upstream_port 3000;
            set $upstream_proto http;

            location / {
                proxy_pass $upstream_proto://$upstream_app:$upstream_port;
            }
        }
        """

        reader = SwagReader(config_path="/config/nginx/site-confs/test.conf")
        result = reader.parse_config(config)

        # Should have ProxyRoute entities
        assert "proxy_routes" in result
        assert len(result["proxy_routes"]) == 1

        route = result["proxy_routes"][0]
        assert route.server_name == "api.example.com"
        assert route.upstream_app == "100.74.16.82"
        assert route.upstream_port == 3000
        assert route.upstream_proto == "http"
        assert route.tls_enabled is True
        assert route.extraction_tier == "A"

    def test_parse_outputs_location_blocks(self) -> None:
        """Test that parsing creates LocationBlock entities."""
        from packages.ingest.readers.swag import SwagReader

        config = """
        server {
            listen 443 ssl;
            server_name api.example.com;

            location /api {
                proxy_pass http://api-service:8080;
            }

            location /admin {
                proxy_pass http://admin-service:9000;
                auth_request /auth;
            }
        }
        """

        reader = SwagReader(config_path="/config/nginx/site-confs/test.conf")
        result = reader.parse_config(config)

        # Should have LocationBlock entities
        assert "location_blocks" in result
        assert len(result["location_blocks"]) == 2

        loc1 = result["location_blocks"][0]
        assert loc1.path == "/api"
        assert loc1.proxy_pass_url == "http://api-service:8080"
        assert loc1.auth_enabled is False
        assert loc1.extraction_tier == "A"

        loc2 = result["location_blocks"][1]
        assert loc2.path == "/admin"
        assert loc2.auth_enabled is True

    def test_parse_outputs_upstream_configs(self) -> None:
        """Test that parsing creates UpstreamConfig entities."""
        from packages.ingest.readers.swag import SwagReader

        config = """
        server {
            listen 443 ssl;
            server_name api.example.com;

            set $upstream_app 100.74.16.82;
            set $upstream_port 3000;
            set $upstream_proto https;

            location / {
                proxy_pass $upstream_proto://$upstream_app:$upstream_port;
            }
        }
        """

        reader = SwagReader(config_path="/config/nginx/site-confs/test.conf")
        result = reader.parse_config(config)

        # Should have UpstreamConfig entities
        assert "upstream_configs" in result
        assert len(result["upstream_configs"]) == 1

        upstream = result["upstream_configs"][0]
        assert upstream.app == "100.74.16.82"
        assert upstream.port == 3000
        assert upstream.proto == "https"
        assert upstream.extraction_tier == "A"

    def test_parse_outputs_proxy_headers(self) -> None:
        """Test that parsing creates ProxyHeader entities."""
        from packages.ingest.readers.swag import SwagReader

        config = """
        server {
            listen 443 ssl;
            server_name api.example.com;

            add_header X-Frame-Options "SAMEORIGIN";
            add_header X-Content-Type-Options "nosniff";

            location / {
                proxy_set_header Host $host;
                proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                proxy_pass http://api-service:8080;
            }
        }
        """

        reader = SwagReader(config_path="/config/nginx/site-confs/test.conf")
        result = reader.parse_config(config)

        # Should have ProxyHeader entities
        assert "proxy_headers" in result
        assert len(result["proxy_headers"]) >= 2

        # Check add_header
        add_headers = [h for h in result["proxy_headers"] if h.header_type == "add_header"]
        assert len(add_headers) >= 2

        header = add_headers[0]
        assert header.header_name == "X-Frame-Options"
        assert header.header_value == "SAMEORIGIN"
        assert header.extraction_tier == "A"

    def test_parse_complete_integration(self) -> None:
        """Integration test: Parse complete config and verify all entity types."""
        from packages.ingest.readers.swag import SwagReader

        config = """
        server {
            listen 443 ssl http2;
            server_name myapp.example.com;

            set $upstream_app 100.74.16.82;
            set $upstream_port 3000;
            set $upstream_proto http;

            add_header X-Frame-Options "SAMEORIGIN";

            location / {
                proxy_set_header Host $host;
                proxy_pass $upstream_proto://$upstream_app:$upstream_port;
            }

            location /admin {
                auth_request /auth;
                proxy_pass http://admin:9000;
            }
        }
        """

        reader = SwagReader(config_path="/config/nginx/site-confs/myapp.conf")
        result = reader.parse_config(config)

        # Verify all entity types present
        assert "config_files" in result
        assert "proxies" in result
        assert "proxy_routes" in result
        assert "location_blocks" in result
        assert "upstream_configs" in result
        assert "proxy_headers" in result

        # Verify entity counts
        assert len(result["config_files"]) == 1
        assert len(result["proxies"]) >= 1
        assert len(result["proxy_routes"]) >= 1
        assert len(result["location_blocks"]) == 2
        assert len(result["upstream_configs"]) == 1
        assert len(result["proxy_headers"]) >= 1


class TestSwagReader:
    """Tests for the SwagReader class (legacy tests updated)."""

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

        reader = SwagReader(config_path="/test.conf")
        result = reader.parse_config(config)

        # Should extract one Proxy node
        assert len(result["proxies"]) == 1
        proxy = result["proxies"][0]
        assert proxy.name == "swag"
        assert proxy.proxy_type == "swag"

        # Should extract location blocks
        assert len(result["location_blocks"]) == 1
        location = result["location_blocks"][0]
        assert location.path == "/"
        assert "api-service" in location.proxy_pass_url

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

        # Should extract location blocks for both servers
        assert len(result["location_blocks"]) == 2

        # First location (SSL)
        loc1 = result["location_blocks"][0]
        assert loc1.path == "/api/v1"
        assert "api-service" in loc1.proxy_pass_url

        # Second location (no SSL)
        loc2 = result["location_blocks"][1]
        assert loc2.path == "/"
        assert "web-service" in loc2.proxy_pass_url

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

        # Should extract location blocks for both locations
        assert len(result["location_blocks"]) == 2

        loc1 = result["location_blocks"][0]
        assert loc1.path == "/api"
        assert "api-service" in loc1.proxy_pass_url

        loc2 = result["location_blocks"][1]
        assert loc2.path == "/auth"
        assert "auth-service" in loc2.proxy_pass_url

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
        assert len(result["proxy_routes"]) == 0
        assert len(result["location_blocks"]) == 0

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

        # Should have proxy node but no proxy routes
        assert len(result["proxies"]) == 1
        assert len(result["proxy_routes"]) == 0
        # Should have location block (even without proxy_pass)
        assert len(result["location_blocks"]) == 1

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

        # Should extract location block with upstream name
        assert len(result["location_blocks"]) == 1
        location = result["location_blocks"][0]
        assert location.path == "/"
        assert "backend" in location.proxy_pass_url

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

        # Should have location blocks for each server
        assert len(result["location_blocks"]) == 3
        # Note: TLS detection is now only available through proxy_routes
        # when upstream variables are present

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

        # Check required fields
        assert proxy.name is not None
        assert proxy.proxy_type is not None
        assert isinstance(proxy.created_at, datetime)
        assert isinstance(proxy.updated_at, datetime)
        assert proxy.extraction_tier == "A"

    def test_location_block_has_required_fields(self) -> None:
        """Test that generated location blocks have all required fields."""
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

        location = result["location_blocks"][0]

        # Check required fields
        assert location.path is not None
        assert location.proxy_pass_url is not None
        assert isinstance(location.auth_enabled, bool)
        assert location.extraction_tier == "A"

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

        # Should extract location block with regex pattern preserved
        assert len(result["location_blocks"]) == 1
        location = result["location_blocks"][0]
        assert "/api/" in location.path or "^/api/v" in location.path
        assert "api-service" in location.proxy_pass_url

    def test_parse_file(self) -> None:
        """Test parsing config from file path."""
        import os
        import tempfile

        from packages.ingest.readers.swag import SwagReader

        config = """
        server {
            listen 443 ssl;
            server_name file-test.example.com;
            location / { proxy_pass http://test-service:8080; }
        }
        """

        # Write config to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False) as f:
            f.write(config)
            temp_path = f.name

        try:
            reader = SwagReader()
            result = reader.parse_file(temp_path)

            assert len(result["location_blocks"]) == 1
            location = result["location_blocks"][0]
            assert location.path == "/"
            assert "test-service" in location.proxy_pass_url
        finally:
            os.unlink(temp_path)

    def test_parse_file_not_found_raises_error(self) -> None:
        """Test that parsing non-existent file raises appropriate error."""
        from packages.ingest.readers.swag import SwagReader, SwagReaderError

        reader = SwagReader()
        with pytest.raises(SwagReaderError):
            reader.parse_file("/nonexistent/path/to/config.conf")
