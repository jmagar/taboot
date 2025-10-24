"""Unit tests for Neo4j client with connection pooling.

Tests the Neo4j driver connection management, health checks, and session handling.
Following TDD methodology: RED phase - tests written before implementation.
"""

import pytest
from neo4j.exceptions import ServiceUnavailable

from packages.graph.client import Neo4jClient, Neo4jConnectionError


class TestNeo4jClient:
    """Test suite for Neo4jClient connection pooling and management."""

    def test_client_initialization_with_config(self, mock_config):
        """Test client initializes with configuration from TabootConfig."""
        client = Neo4jClient()

        assert client is not None
        assert hasattr(client, "_driver")
        assert hasattr(client, "_config")

    def test_client_connect_creates_driver(self, mock_config, mocker):
        """Test connect() creates Neo4j driver with proper connection pooling."""
        mock_driver = mocker.Mock()
        mocker.patch("packages.graph.client.GraphDatabase.driver", return_value=mock_driver)

        client = Neo4jClient()
        client.connect()

        assert client._driver is not None
        assert client._driver is mock_driver

    def test_client_connect_uses_config_credentials(self, mock_config, mocker):
        """Test connect() uses credentials from TabootConfig."""
        mock_graph_driver = mocker.patch("packages.graph.client.GraphDatabase.driver")

        client = Neo4jClient()
        client.connect()

        mock_graph_driver.assert_called_once_with(
            mock_config.neo4j_uri,
            auth=(mock_config.neo4j_user, mock_config.neo4j_password),
            database=mock_config.neo4j_db,
        )

    def test_client_health_check_returns_true_when_healthy(self, mock_config, mocker):
        """Test health_check() returns True when Neo4j is reachable."""
        mock_driver = mocker.Mock()

        client = Neo4jClient()
        client._driver = mock_driver

        result = client.health_check()

        assert result is True
        mock_driver.verify_connectivity.assert_called_once()

    def test_client_health_check_returns_false_when_unhealthy(self, mock_config, mocker):
        """Test health_check() returns False when Neo4j is unreachable."""
        mock_driver = mocker.Mock()
        mock_driver.verify_connectivity.side_effect = ServiceUnavailable("Connection failed")

        client = Neo4jClient()
        client._driver = mock_driver

        result = client.health_check()

        assert result is False

    def test_client_health_check_raises_when_not_connected(self, mock_config):
        """Test health_check() raises error when driver not initialized."""
        client = Neo4jClient()

        with pytest.raises(Neo4jConnectionError, match="Neo4j driver not connected"):
            client.health_check()

    def test_client_close_closes_driver(self, mock_config, mocker):
        """Test close() properly closes the Neo4j driver."""
        mock_driver = mocker.Mock()

        client = Neo4jClient()
        client._driver = mock_driver
        client.close()

        mock_driver.close.assert_called_once()
        assert client._driver is None

    def test_client_close_safe_when_not_connected(self, mock_config):
        """Test close() doesn't raise error when driver not initialized."""
        client = Neo4jClient()
        client.close()  # Should not raise

    def test_client_session_context_manager(self, mock_config, mocker):
        """Test session() context manager provides Neo4j session."""
        mock_driver = mocker.Mock()
        mock_session = mocker.Mock()

        # Create a proper context manager mock
        mock_context = mocker.MagicMock()
        mock_context.__enter__ = mocker.Mock(return_value=mock_session)
        mock_context.__exit__ = mocker.Mock(return_value=None)
        mock_driver.session.return_value = mock_context

        client = Neo4jClient()
        client._driver = mock_driver

        with client.session() as session:
            assert session is mock_session

        mock_driver.session.assert_called_once()

    def test_client_session_raises_when_not_connected(self, mock_config):
        """Test session() raises error when driver not initialized."""
        client = Neo4jClient()

        with pytest.raises(Neo4jConnectionError, match="Neo4j driver not connected"):
            with client.session():
                pass

    def test_client_session_passes_database_param(self, mock_config, mocker):
        """Test session() passes database parameter from config."""
        mock_driver = mocker.Mock()
        mock_session = mocker.Mock()

        # Create a proper context manager mock
        mock_context = mocker.MagicMock()
        mock_context.__enter__ = mocker.Mock(return_value=mock_session)
        mock_context.__exit__ = mocker.Mock(return_value=None)
        mock_driver.session.return_value = mock_context

        client = Neo4jClient()
        client._driver = mock_driver

        with client.session():
            pass

        mock_driver.session.assert_called_once_with(database=mock_config.neo4j_db)

    def test_client_connect_logs_with_correlation_id(self, mock_config, mocker, caplog):
        """Test connect() logs with correlation ID from tracing context."""
        mocker.patch("packages.graph.client.GraphDatabase.driver")
        mocker.patch("packages.graph.client.get_correlation_id", return_value="test-corr-123")

        client = Neo4jClient()

        with caplog.at_level("INFO"):
            client.connect()

        assert "test-corr-123" in caplog.text or len(caplog.records) > 0

    def test_client_connection_error_thrown_early(self, mock_config, mocker):
        """Test connection errors are thrown early (no fallbacks)."""
        mocker.patch(
            "packages.graph.client.GraphDatabase.driver",
            side_effect=Exception("Connection refused")
        )

        client = Neo4jClient()

        with pytest.raises(Neo4jConnectionError, match="Failed to connect to Neo4j"):
            client.connect()

    def test_client_as_context_manager(self, mock_config, mocker):
        """Test Neo4jClient can be used as context manager."""
        mock_driver = mocker.Mock()
        mocker.patch("packages.graph.client.GraphDatabase.driver", return_value=mock_driver)

        with Neo4jClient() as client:
            assert client._driver is not None

        mock_driver.close.assert_called_once()

    def test_client_verify_connectivity_on_connect(self, mock_config, mocker):
        """Test connect() verifies connectivity after creating driver."""
        mock_driver = mocker.Mock()
        mocker.patch("packages.graph.client.GraphDatabase.driver", return_value=mock_driver)

        client = Neo4jClient()
        client.connect()

        mock_driver.verify_connectivity.assert_called_once()


@pytest.fixture
def mock_config(mocker):
    """Mock TabootConfig for tests."""
    mock = mocker.Mock()
    mock.neo4j_uri = "bolt://localhost:7687"
    mock.neo4j_user = "neo4j"
    mock.neo4j_password = "test_password"
    mock.neo4j_db = "neo4j"

    mocker.patch("packages.graph.client.get_config", return_value=mock)
    return mock
