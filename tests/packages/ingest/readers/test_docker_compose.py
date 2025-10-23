"""Tests for DockerComposeReader.

Tests Docker Compose YAML parsing following TDD methodology (RED-GREEN-REFACTOR).
Extracts Service nodes, DEPENDS_ON relationships, and BINDS relationships.
"""

from pathlib import Path

import pytest


class TestDockerComposeReader:
    """Tests for the DockerComposeReader class."""

    @pytest.fixture
    def sample_compose_yaml(self, tmp_path: Path) -> Path:
        """Create a sample docker-compose.yaml for testing.

        Args:
            tmp_path: pytest temporary directory fixture.

        Returns:
            Path: Path to the created docker-compose.yaml file.
        """
        compose_content = """
version: '3.8'

services:
  web:
    image: nginx:latest
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - api
      - cache

  api:
    image: myapp/api:v1.2.3
    ports:
      - "8080:8080"
    depends_on:
      - db

  db:
    image: postgres:15
    ports:
      - "5432:5432"

  cache:
    image: redis:7
    ports:
      - "6379:6379"
"""
        compose_file = tmp_path / "docker-compose.yaml"
        compose_file.write_text(compose_content)
        return compose_file

    @pytest.fixture
    def minimal_compose_yaml(self, tmp_path: Path) -> Path:
        """Create a minimal docker-compose.yaml with single service.

        Args:
            tmp_path: pytest temporary directory fixture.

        Returns:
            Path: Path to the created docker-compose.yaml file.
        """
        compose_content = """
version: '3.8'

services:
  minimal:
    image: alpine:latest
"""
        compose_file = tmp_path / "minimal-compose.yaml"
        compose_file.write_text(compose_content)
        return compose_file

    def test_reader_parses_services(self, sample_compose_yaml: Path) -> None:
        """Test that DockerComposeReader extracts Service nodes."""
        from packages.ingest.readers.docker_compose import DockerComposeReader

        reader = DockerComposeReader()
        result = reader.load_data(str(sample_compose_yaml))

        # Should extract 4 services: web, api, db, cache
        assert "services" in result
        services = result["services"]
        assert len(services) == 4

        # Verify service names
        service_names = {svc["name"] for svc in services}
        assert service_names == {"web", "api", "db", "cache"}

    def test_reader_extracts_service_images(self, sample_compose_yaml: Path) -> None:
        """Test that DockerComposeReader extracts image information."""
        from packages.ingest.readers.docker_compose import DockerComposeReader

        reader = DockerComposeReader()
        result = reader.load_data(str(sample_compose_yaml))

        services = {svc["name"]: svc for svc in result["services"]}

        assert services["web"]["image"] == "nginx:latest"
        assert services["api"]["image"] == "myapp/api:v1.2.3"
        assert services["db"]["image"] == "postgres:15"
        assert services["cache"]["image"] == "redis:7"

    def test_reader_extracts_depends_on_relationships(self, sample_compose_yaml: Path) -> None:
        """Test that DockerComposeReader extracts DEPENDS_ON relationships."""
        from packages.ingest.readers.docker_compose import DockerComposeReader

        reader = DockerComposeReader()
        result = reader.load_data(str(sample_compose_yaml))

        assert "relationships" in result
        relationships = result["relationships"]

        # Filter DEPENDS_ON relationships
        depends_on = [r for r in relationships if r["type"] == "DEPENDS_ON"]

        # web depends on api and cache
        # api depends on db
        # Total: 3 DEPENDS_ON relationships
        assert len(depends_on) == 3

        # Verify specific relationships
        web_deps = [r for r in depends_on if r["source"] == "web"]
        assert len(web_deps) == 2
        web_targets = {r["target"] for r in web_deps}
        assert web_targets == {"api", "cache"}

        api_deps = [r for r in depends_on if r["source"] == "api"]
        assert len(api_deps) == 1
        assert api_deps[0]["target"] == "db"

    def test_reader_extracts_port_bindings(self, sample_compose_yaml: Path) -> None:
        """Test that DockerComposeReader extracts BINDS relationships for ports."""
        from packages.ingest.readers.docker_compose import DockerComposeReader

        reader = DockerComposeReader()
        result = reader.load_data(str(sample_compose_yaml))

        relationships = result["relationships"]

        # Filter BINDS relationships
        binds = [r for r in relationships if r["type"] == "BINDS"]

        # web: 2 ports, api: 1 port, db: 1 port, cache: 1 port = 5 total
        assert len(binds) == 5

        # Verify web port bindings
        web_binds = [r for r in binds if r["source"] == "web"]
        assert len(web_binds) == 2

        web_ports = {r["port"] for r in web_binds}
        assert web_ports == {80, 443}

        # All should have protocol tcp by default
        assert all(r["protocol"] == "tcp" for r in web_binds)

    def test_reader_validates_port_range(self, tmp_path: Path) -> None:
        """Test that DockerComposeReader validates port numbers (1-65535)."""
        from packages.ingest.readers.docker_compose import (
            DockerComposeReader,
            InvalidPortError,
        )

        # Create compose file with invalid port
        compose_content = """
version: '3.8'

services:
  invalid:
    image: test:latest
    ports:
      - "99999:8080"
"""
        compose_file = tmp_path / "invalid-port.yaml"
        compose_file.write_text(compose_content)

        reader = DockerComposeReader()

        with pytest.raises(InvalidPortError, match="Port.*must be between 1 and 65535"):
            reader.load_data(str(compose_file))

    def test_reader_handles_missing_file(self) -> None:
        """Test that DockerComposeReader raises error for missing file."""
        from packages.ingest.readers.docker_compose import (
            DockerComposeError,
            DockerComposeReader,
        )

        reader = DockerComposeReader()

        with pytest.raises(DockerComposeError, match="File not found"):
            reader.load_data("/nonexistent/docker-compose.yaml")

    def test_reader_handles_invalid_yaml(self, tmp_path: Path) -> None:
        """Test that DockerComposeReader raises error for invalid YAML."""
        from packages.ingest.readers.docker_compose import (
            DockerComposeReader,
            InvalidYAMLError,
        )

        # Create invalid YAML file
        invalid_file = tmp_path / "invalid.yaml"
        invalid_file.write_text("invalid: yaml: content: [[[")

        reader = DockerComposeReader()

        with pytest.raises(InvalidYAMLError, match="Invalid YAML"):
            reader.load_data(str(invalid_file))

    def test_reader_handles_empty_services(self, tmp_path: Path) -> None:
        """Test that DockerComposeReader handles compose file with no services."""
        from packages.ingest.readers.docker_compose import DockerComposeReader

        compose_content = """
version: '3.8'

services: {}
"""
        compose_file = tmp_path / "empty.yaml"
        compose_file.write_text(compose_content)

        reader = DockerComposeReader()
        result = reader.load_data(str(compose_file))

        assert result["services"] == []
        assert result["relationships"] == []

    def test_reader_handles_service_without_ports(self, minimal_compose_yaml: Path) -> None:
        """Test that DockerComposeReader handles services without port bindings."""
        from packages.ingest.readers.docker_compose import DockerComposeReader

        reader = DockerComposeReader()
        result = reader.load_data(str(minimal_compose_yaml))

        assert len(result["services"]) == 1
        assert result["services"][0]["name"] == "minimal"

        # No port bindings
        binds = [r for r in result["relationships"] if r["type"] == "BINDS"]
        assert len(binds) == 0

    def test_reader_requires_file_path(self) -> None:
        """Test that DockerComposeReader requires file_path parameter."""
        from packages.ingest.readers.docker_compose import DockerComposeReader

        reader = DockerComposeReader()

        with pytest.raises(ValueError, match="file_path cannot be empty"):
            reader.load_data("")

    def test_reader_returns_structured_data(self, sample_compose_yaml: Path) -> None:
        """Test that DockerComposeReader returns properly structured data."""
        from packages.ingest.readers.docker_compose import DockerComposeReader

        reader = DockerComposeReader()
        result = reader.load_data(str(sample_compose_yaml))

        # Verify top-level structure
        assert isinstance(result, dict)
        assert "services" in result
        assert "relationships" in result

        # Verify services structure
        assert isinstance(result["services"], list)
        for service in result["services"]:
            assert "name" in service
            assert "image" in service
            assert isinstance(service["name"], str)
            assert isinstance(service["image"], str)

        # Verify relationships structure
        assert isinstance(result["relationships"], list)
        for rel in result["relationships"]:
            assert "type" in rel
            assert "source" in rel
            assert rel["type"] in ["DEPENDS_ON", "BINDS"]

    def test_reader_handles_port_with_protocol(self, tmp_path: Path) -> None:
        """Test that DockerComposeReader handles port definitions with protocol."""
        from packages.ingest.readers.docker_compose import DockerComposeReader

        compose_content = """
version: '3.8'

services:
  dns:
    image: dns-server:latest
    ports:
      - "53:53/udp"
      - "53:53/tcp"
"""
        compose_file = tmp_path / "protocol.yaml"
        compose_file.write_text(compose_content)

        reader = DockerComposeReader()
        result = reader.load_data(str(compose_file))

        binds = [r for r in result["relationships"] if r["type"] == "BINDS"]
        assert len(binds) == 2

        # Check protocols
        protocols = {r["protocol"] for r in binds}
        assert protocols == {"tcp", "udp"}

    def test_reader_parses_version_from_image(self, sample_compose_yaml: Path) -> None:
        """Test that DockerComposeReader extracts version from image tag."""
        from packages.ingest.readers.docker_compose import DockerComposeReader

        reader = DockerComposeReader()
        result = reader.load_data(str(sample_compose_yaml))

        services = {svc["name"]: svc for svc in result["services"]}

        # Service with explicit version tag
        assert services["api"]["version"] == "v1.2.3"

        # Service with 'latest' tag should have version 'latest'
        assert services["web"]["version"] == "latest"

        # Service with numeric version
        assert services["db"]["version"] == "15"
