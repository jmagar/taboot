"""Unit tests for SwagGraphWriter.

Tests batched Neo4j writes for SWAG entities using the new schema:
- SwagConfigFile
- Proxy
- ProxyRoute
- LocationBlock
- UpstreamConfig
- ProxyHeader
"""

from datetime import datetime, UTC
from unittest.mock import MagicMock, call

import pytest

from packages.graph.client import Neo4jClient
from packages.graph.writers.swag_writer import SwagGraphWriter
from packages.schemas.swag import (
    LocationBlock,
    Proxy,
    ProxyHeader,
    ProxyRoute,
    SwagConfigFile,
    UpstreamConfig,
)


@pytest.fixture
def mock_neo4j_client() -> MagicMock:
    """Create a mock Neo4j client for testing."""
    client = MagicMock(spec=Neo4jClient)
    session = MagicMock()
    client.session.return_value.__enter__.return_value = session
    client.session.return_value.__exit__.return_value = None

    # Mock result and summary
    result = MagicMock()
    summary = MagicMock()
    summary.counters = {"nodes_created": 1, "relationships_created": 0}
    result.consume.return_value = summary
    session.run.return_value = result

    return client


@pytest.fixture
def swag_writer(mock_neo4j_client: MagicMock) -> SwagGraphWriter:
    """Create SwagGraphWriter instance with mock client."""
    return SwagGraphWriter(neo4j_client=mock_neo4j_client, batch_size=2)


@pytest.fixture
def sample_swag_config_file() -> SwagConfigFile:
    """Create sample SwagConfigFile entity."""
    return SwagConfigFile(
        file_path="/config/nginx/site-confs/myapp.conf",
        version="1.0",
        parsed_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        created_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        updated_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        source_timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        extraction_tier="A",
        extraction_method="nginx_parser",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_proxy() -> Proxy:
    """Create sample Proxy entity."""
    return Proxy(
        name="myapp-proxy",
        proxy_type="swag",
        config_path="/config/nginx/site-confs/myapp.conf",
        created_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        updated_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        source_timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        extraction_tier="A",
        extraction_method="nginx_parser",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_proxy_route() -> ProxyRoute:
    """Create sample ProxyRoute entity."""
    return ProxyRoute(
        server_name="myapp.example.com",
        upstream_app="100.74.16.82",
        upstream_port=3000,
        upstream_proto="http",
        tls_enabled=True,
        created_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        updated_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        source_timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        extraction_tier="A",
        extraction_method="nginx_parser",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_location_block() -> LocationBlock:
    """Create sample LocationBlock entity."""
    return LocationBlock(
        path="/api",
        proxy_pass_url="http://backend:8080",
        auth_enabled=True,
        auth_type="authelia",
        created_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        updated_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        source_timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        extraction_tier="A",
        extraction_method="nginx_parser",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_upstream_config() -> UpstreamConfig:
    """Create sample UpstreamConfig entity."""
    return UpstreamConfig(
        app="100.74.16.82",
        port=3000,
        proto="http",
        created_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        updated_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        source_timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        extraction_tier="A",
        extraction_method="nginx_parser",
        confidence=1.0,
        extractor_version="1.0.0",
    )


@pytest.fixture
def sample_proxy_header() -> ProxyHeader:
    """Create sample ProxyHeader entity."""
    return ProxyHeader(
        header_name="X-Frame-Options",
        header_value="SAMEORIGIN",
        header_type="add_header",
        created_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        updated_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        source_timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        extraction_tier="A",
        extraction_method="nginx_parser",
        confidence=1.0,
        extractor_version="1.0.0",
    )


class TestSwagGraphWriterInit:
    """Test SwagGraphWriter initialization."""

    def test_init_with_defaults(self, mock_neo4j_client: MagicMock) -> None:
        """Test initialization with default batch size."""
        writer = SwagGraphWriter(neo4j_client=mock_neo4j_client)

        assert writer.neo4j_client == mock_neo4j_client
        assert writer.batch_size == 2000

    def test_init_with_custom_batch_size(self, mock_neo4j_client: MagicMock) -> None:
        """Test initialization with custom batch size."""
        writer = SwagGraphWriter(neo4j_client=mock_neo4j_client, batch_size=500)

        assert writer.neo4j_client == mock_neo4j_client
        assert writer.batch_size == 500


class TestWriteSwagConfigFiles:
    """Test write_swag_config_files method."""

    def test_write_empty_list(self, swag_writer: SwagGraphWriter) -> None:
        """Test writing empty config file list."""
        result = swag_writer.write_swag_config_files([])

        assert result == {"total_written": 0, "batches_executed": 0}

    def test_write_single_config_file(
        self,
        swag_writer: SwagGraphWriter,
        mock_neo4j_client: MagicMock,
        sample_swag_config_file: SwagConfigFile,
    ) -> None:
        """Test writing single config file."""
        result = swag_writer.write_swag_config_files([sample_swag_config_file])

        assert result == {"total_written": 1, "batches_executed": 1}

        session = mock_neo4j_client.session.return_value.__enter__.return_value
        assert session.run.call_count == 1

        # Verify query contains expected fields
        call_args = session.run.call_args
        query = call_args[0][0]
        assert "SwagConfigFile" in query
        assert "file_path" in query
        assert "extraction_tier" in query

    def test_write_multiple_config_files(
        self,
        swag_writer: SwagGraphWriter,
        mock_neo4j_client: MagicMock,
        sample_swag_config_file: SwagConfigFile,
    ) -> None:
        """Test writing multiple config files with batching."""
        # Create 3 config files (batch size is 2)
        config_files = [
            sample_swag_config_file,
            SwagConfigFile(
                file_path="/config/nginx/site-confs/app2.conf",
                version="1.0",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                extraction_tier="A",
                extraction_method="nginx_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            ),
            SwagConfigFile(
                file_path="/config/nginx/site-confs/app3.conf",
                version="1.0",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                extraction_tier="A",
                extraction_method="nginx_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            ),
        ]

        result = swag_writer.write_swag_config_files(config_files)

        assert result == {"total_written": 3, "batches_executed": 2}

        session = mock_neo4j_client.session.return_value.__enter__.return_value
        assert session.run.call_count == 2  # 2 batches


class TestWriteProxies:
    """Test write_proxies method."""

    def test_write_empty_list(self, swag_writer: SwagGraphWriter) -> None:
        """Test writing empty proxy list."""
        result = swag_writer.write_proxies([])

        assert result == {"total_written": 0, "batches_executed": 0}

    def test_write_single_proxy(
        self,
        swag_writer: SwagGraphWriter,
        mock_neo4j_client: MagicMock,
        sample_proxy: Proxy,
    ) -> None:
        """Test writing single proxy."""
        result = swag_writer.write_proxies([sample_proxy])

        assert result == {"total_written": 1, "batches_executed": 1}

        session = mock_neo4j_client.session.return_value.__enter__.return_value
        assert session.run.call_count == 1

        # Verify query contains expected fields
        call_args = session.run.call_args
        query = call_args[0][0]
        assert "Proxy" in query
        assert "name" in query
        assert "proxy_type" in query
        assert "extraction_tier" in query


class TestWriteProxyRoutes:
    """Test write_proxy_routes method."""

    def test_write_empty_proxy_name_raises(
        self, swag_writer: SwagGraphWriter, sample_proxy_route: ProxyRoute
    ) -> None:
        """Test that empty proxy_name raises ValueError."""
        with pytest.raises(ValueError, match="proxy_name cannot be empty"):
            swag_writer.write_proxy_routes("", [sample_proxy_route])

    def test_write_empty_routes(self, swag_writer: SwagGraphWriter) -> None:
        """Test writing empty routes list."""
        result = swag_writer.write_proxy_routes("myapp-proxy", [])

        assert result == {"total_written": 0, "batches_executed": 0}

    def test_write_single_route(
        self,
        swag_writer: SwagGraphWriter,
        mock_neo4j_client: MagicMock,
        sample_proxy_route: ProxyRoute,
    ) -> None:
        """Test writing single proxy route."""
        result = swag_writer.write_proxy_routes("myapp-proxy", [sample_proxy_route])

        assert result == {"total_written": 1, "batches_executed": 1}

        session = mock_neo4j_client.session.return_value.__enter__.return_value
        assert session.run.call_count == 1

        # Verify query contains expected fields
        call_args = session.run.call_args
        query = call_args[0][0]
        assert "ProxyRoute" in query
        assert "server_name" in query
        assert "upstream_app" in query
        assert "ROUTES_TO" in query


class TestWriteLocationBlocks:
    """Test write_location_blocks method."""

    def test_write_empty_proxy_name_raises(
        self, swag_writer: SwagGraphWriter, sample_location_block: LocationBlock
    ) -> None:
        """Test that empty proxy_name raises ValueError."""
        with pytest.raises(ValueError, match="proxy_name cannot be empty"):
            swag_writer.write_location_blocks("", [sample_location_block])

    def test_write_empty_locations(self, swag_writer: SwagGraphWriter) -> None:
        """Test writing empty locations list."""
        result = swag_writer.write_location_blocks("myapp-proxy", [])

        assert result == {"total_written": 0, "batches_executed": 0}

    def test_write_single_location(
        self,
        swag_writer: SwagGraphWriter,
        mock_neo4j_client: MagicMock,
        sample_location_block: LocationBlock,
    ) -> None:
        """Test writing single location block."""
        result = swag_writer.write_location_blocks("myapp-proxy", [sample_location_block])

        assert result == {"total_written": 1, "batches_executed": 1}

        session = mock_neo4j_client.session.return_value.__enter__.return_value
        assert session.run.call_count == 1

        # Verify query contains expected fields
        call_args = session.run.call_args
        query = call_args[0][0]
        assert "LocationBlock" in query
        assert "path" in query
        assert "auth_enabled" in query
        assert "HAS_LOCATION" in query


class TestWriteUpstreamConfigs:
    """Test write_upstream_configs method."""

    def test_write_empty_proxy_name_raises(
        self, swag_writer: SwagGraphWriter, sample_upstream_config: UpstreamConfig
    ) -> None:
        """Test that empty proxy_name raises ValueError."""
        with pytest.raises(ValueError, match="proxy_name cannot be empty"):
            swag_writer.write_upstream_configs("", [sample_upstream_config])

    def test_write_empty_upstreams(self, swag_writer: SwagGraphWriter) -> None:
        """Test writing empty upstreams list."""
        result = swag_writer.write_upstream_configs("myapp-proxy", [])

        assert result == {"total_written": 0, "batches_executed": 0}

    def test_write_single_upstream(
        self,
        swag_writer: SwagGraphWriter,
        mock_neo4j_client: MagicMock,
        sample_upstream_config: UpstreamConfig,
    ) -> None:
        """Test writing single upstream config."""
        result = swag_writer.write_upstream_configs("myapp-proxy", [sample_upstream_config])

        assert result == {"total_written": 1, "batches_executed": 1}

        session = mock_neo4j_client.session.return_value.__enter__.return_value
        assert session.run.call_count == 1

        # Verify query contains expected fields
        call_args = session.run.call_args
        query = call_args[0][0]
        assert "UpstreamConfig" in query
        assert "app" in query
        assert "port" in query
        assert "HAS_UPSTREAM" in query


class TestWriteProxyHeaders:
    """Test write_proxy_headers method."""

    def test_write_empty_proxy_name_raises(
        self, swag_writer: SwagGraphWriter, sample_proxy_header: ProxyHeader
    ) -> None:
        """Test that empty proxy_name raises ValueError."""
        with pytest.raises(ValueError, match="proxy_name cannot be empty"):
            swag_writer.write_proxy_headers("", [sample_proxy_header])

    def test_write_empty_headers(self, swag_writer: SwagGraphWriter) -> None:
        """Test writing empty headers list."""
        result = swag_writer.write_proxy_headers("myapp-proxy", [])

        assert result == {"total_written": 0, "batches_executed": 0}

    def test_write_single_header(
        self,
        swag_writer: SwagGraphWriter,
        mock_neo4j_client: MagicMock,
        sample_proxy_header: ProxyHeader,
    ) -> None:
        """Test writing single proxy header."""
        result = swag_writer.write_proxy_headers("myapp-proxy", [sample_proxy_header])

        assert result == {"total_written": 1, "batches_executed": 1}

        session = mock_neo4j_client.session.return_value.__enter__.return_value
        assert session.run.call_count == 1

        # Verify query contains expected fields
        call_args = session.run.call_args
        query = call_args[0][0]
        assert "ProxyHeader" in query
        assert "header_name" in query
        assert "header_value" in query
        assert "HAS_HEADER" in query


class TestBatching:
    """Test batching behavior across methods."""

    def test_proxy_batching(
        self, swag_writer: SwagGraphWriter, mock_neo4j_client: MagicMock
    ) -> None:
        """Test that proxies are batched correctly."""
        # Create 5 proxies (batch size is 2)
        proxies = [
            Proxy(
                name=f"proxy-{i}",
                proxy_type="swag",
                config_path=f"/config/nginx/site-confs/app{i}.conf",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                extraction_tier="A",
                extraction_method="nginx_parser",
                confidence=1.0,
                extractor_version="1.0.0",
            )
            for i in range(5)
        ]

        result = swag_writer.write_proxies(proxies)

        assert result == {"total_written": 5, "batches_executed": 3}

        session = mock_neo4j_client.session.return_value.__enter__.return_value
        assert session.run.call_count == 3  # 3 batches (2, 2, 1)

        # Verify batch sizes
        calls = session.run.call_args_list
        # session.run is called as run(query, {"rows": batch})
        assert len(calls[0].args[1]["rows"]) == 2  # First batch: 2 items
        assert len(calls[1].args[1]["rows"]) == 2  # Second batch: 2 items
        assert len(calls[2].args[1]["rows"]) == 1  # Third batch: 1 item
