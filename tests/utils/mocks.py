"""Helper functions for constructing common test doubles."""

from typing import Any


def create_mock_neo4j_driver(mocker: Any) -> Any:
    """Create a mocked Neo4j driver with a reusable session context."""

    mock_driver = mocker.MagicMock()
    mock_session = mocker.MagicMock()
    mock_context = mocker.MagicMock()
    mock_context.__enter__.return_value = mock_session
    mock_context.__exit__.return_value = None
    mock_driver.session.return_value = mock_context
    return mock_driver


def create_mock_qdrant_client(mocker: Any) -> Any:
    """Create a mocked Qdrant client instance."""

    return mocker.MagicMock()


def create_mock_redis_client(mocker: Any) -> Any:
    """Create a mocked Redis client instance."""

    return mocker.MagicMock()
