"""Neo4j client with connection pooling and session management.

Provides a connection-pooled Neo4j driver wrapper with health checks,
session context managers, and proper error handling.

Implements requirements from data-model.md and follows project standards:
- Type hints on all functions
- Throw errors early (no fallbacks)
- JSON structured logging
- Correlation ID tracking
"""

from collections.abc import Generator
from contextlib import contextmanager
from types import TracebackType

from neo4j import Driver, GraphDatabase, Session
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from packages.common.config import get_config
from packages.common.logging import get_logger
from packages.common.tracing import get_correlation_id

logger = get_logger(__name__)


class Neo4jConnectionError(Exception):
    """Exception raised when Neo4j connection fails.

    This exception is thrown early when connection issues occur.
    No fallbacks or retries are attempted per project standards.
    """

    pass


class Neo4jClient:
    """Neo4j client with connection pooling and session management.

    Manages Neo4j driver lifecycle with connection pooling, health checks,
    and session context managers. Follows strict error handling (no fallbacks).

    Attributes:
        _driver: Neo4j driver instance with connection pooling.
        _config: TabootConfig instance for connection parameters.

    Example:
        >>> client = Neo4jClient()
        >>> client.connect()
        >>> if client.health_check():
        ...     with client.session() as session:
        ...         result = session.run("MATCH (n) RETURN count(n)")
        >>> client.close()

        Or use as context manager:
        >>> with Neo4jClient() as client:
        ...     with client.session() as session:
        ...         result = session.run("MATCH (n) RETURN count(n)")
    """

    def __init__(self) -> None:
        """Initialize Neo4j client with configuration.

        Loads connection parameters from TabootConfig but does not create
        the driver until connect() is called.
        """
        self._driver: Driver | None = None
        self._config = get_config()

        logger.info(
            "Neo4j client initialized",
            extra={
                "uri": self._config.neo4j_uri,
                "database": self._config.neo4j_db,
                "correlation_id": get_correlation_id(),
            },
        )

    def connect(self) -> None:
        """Create and verify Neo4j driver connection.

        Creates a connection-pooled Neo4j driver and verifies connectivity.
        Throws Neo4jConnectionError early if connection fails.

        Raises:
            Neo4jConnectionError: If connection to Neo4j fails.

        Example:
            >>> client = Neo4jClient()
            >>> client.connect()
        """
        try:
            logger.info(
                "Connecting to Neo4j",
                extra={
                    "uri": self._config.neo4j_uri,
                    "database": self._config.neo4j_db,
                    "correlation_id": get_correlation_id(),
                },
            )

            self._driver = GraphDatabase.driver(
                self._config.neo4j_uri,
                auth=(self._config.neo4j_user, self._config.neo4j_password),
            )

            # Verify connectivity and target database immediately (fail early)
            self._driver.verify_connectivity()
            with self._driver.session(database=self._config.neo4j_db) as session:
                session.run("RETURN 1").consume()

            logger.info(
                "Neo4j connection established",
                extra={
                    "uri": self._config.neo4j_uri,
                    "correlation_id": get_correlation_id(),
                },
            )

        except (Neo4jError, ServiceUnavailable, Exception) as e:
            logger.error(
                "Failed to connect to Neo4j",
                extra={
                    "uri": self._config.neo4j_uri,
                    "error": str(e),
                    "correlation_id": get_correlation_id(),
                },
            )
            raise Neo4jConnectionError(
                f"Failed to connect to Neo4j at {self._config.neo4j_uri}: {e}"
            ) from e

    def close(self) -> None:
        """Close the Neo4j driver connection.

        Safely closes the driver and cleans up connection pool.
        Safe to call even if driver is not connected.

        Example:
            >>> client = Neo4jClient()
            >>> client.connect()
            >>> client.close()
        """
        if self._driver is not None:
            logger.info(
                "Closing Neo4j connection",
                extra={
                    "uri": self._config.neo4j_uri,
                    "correlation_id": get_correlation_id(),
                },
            )
            self._driver.close()
            self._driver = None

    def get_driver(self) -> Driver:
        """Return the active Neo4j driver instance.

        Raises:
            Neo4jConnectionError: If the driver has not been connected.
        """

        if self._driver is None:
            raise Neo4jConnectionError(
                "Neo4j driver not connected. Call connect() before accessing the driver."
            )

        return self._driver

    def health_check(self) -> bool:
        """Check if Neo4j connection is healthy.

        Verifies connectivity to Neo4j database. Returns False if connection
        fails rather than raising exceptions (used for health endpoints).

        Returns:
            bool: True if Neo4j is reachable, False otherwise.

        Raises:
            Neo4jConnectionError: If driver is not connected (call connect() first).

        Example:
            >>> client = Neo4jClient()
            >>> client.connect()
            >>> if client.health_check():
            ...     print("Neo4j is healthy")
        """
        if self._driver is None:
            raise Neo4jConnectionError(
                "Neo4j driver not connected. Call connect() before health_check()."
            )

        try:
            self._driver.verify_connectivity()
            with self._driver.session(database=self._config.neo4j_db) as session:
                session.run("RETURN 1").consume()
            return True
        except (Neo4jError, ServiceUnavailable) as e:
            logger.warning(
                "Neo4j health check failed",
                extra={
                    "error": str(e),
                    "correlation_id": get_correlation_id(),
                },
            )
            return False

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Create a Neo4j session context manager.

        Provides a session for executing Cypher queries within a context.
        The session is automatically closed when the context exits.

        Yields:
            Session: Neo4j session for executing queries.

        Raises:
            Neo4jConnectionError: If driver is not connected (call connect() first).

        Example:
            >>> client = Neo4jClient()
            >>> client.connect()
            >>> with client.session() as session:
            ...     result = session.run("MATCH (n:Service) RETURN n.name LIMIT 10")
            ...     for record in result:
            ...         print(record["n.name"])
        """
        if self._driver is None:
            raise Neo4jConnectionError(
                "Neo4j driver not connected. Call connect() before session()."
            )

        with self._driver.session(database=self._config.neo4j_db) as session:
            yield session

    def __enter__(self) -> "Neo4jClient":
        """Enter context manager and establish connection.

        Returns:
            Neo4jClient: This client instance with active connection.

        Example:
            >>> with Neo4jClient() as client:
            ...     with client.session() as session:
            ...         result = session.run("MATCH (n) RETURN count(n)")
        """
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context manager and close connection."""
        self.close()


# Export public API
__all__ = ["Neo4jClient", "Neo4jConnectionError"]
