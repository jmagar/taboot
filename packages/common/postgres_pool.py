"""PostgreSQL connection pool for Taboot.

Provides a thread-safe connection pool for PostgreSQL using psycopg2.
Manages connection lifecycle with proper pooling and resource cleanup.
"""

from collections.abc import Generator
from contextlib import contextmanager

import psycopg2
from psycopg2.extensions import connection as PgConnection  # noqa: N812
from psycopg2.pool import ThreadedConnectionPool

from packages.common.config import TabootConfig
from packages.common.logging import get_logger

logger = get_logger(__name__)


class PostgresPoolError(Exception):
    """Exception raised when PostgreSQL pool operations fail."""

    pass


class PostgresPool:
    """Thread-safe PostgreSQL connection pool.

    Manages a pool of PostgreSQL connections with configurable min/max sizes.
    Provides connection checkout/release and automatic cleanup on shutdown.

    Attributes:
        pool: The underlying ThreadedConnectionPool instance.
        _config: TabootConfig instance for connection parameters.

    Example:
        >>> pool = PostgresPool(config)
        >>> with pool.get_connection() as conn:
        ...     with conn.cursor() as cur:
        ...         cur.execute("SELECT 1")
        >>> pool.close_all()

        Or use as context manager:
        >>> with PostgresPool(config) as pool:
        ...     with pool.get_connection() as conn:
        ...         # Use connection
        ...         pass
    """

    def __init__(self, config: TabootConfig) -> None:
        """Initialize PostgreSQL connection pool.

        Args:
            config: TabootConfig instance with PostgreSQL connection parameters.

        Raises:
            PostgresPoolError: If pool initialization fails.
        """
        self._config = config

        try:
            self.pool = ThreadedConnectionPool(
                minconn=config.postgres_min_pool_size,
                maxconn=config.postgres_max_pool_size,
                host=config.postgres_host,
                port=config.postgres_port,
                database=config.postgres_db,
                user=config.postgres_user,
                password=config.postgres_password.get_secret_value(),
            )
            logger.info(
                "PostgreSQL connection pool initialized",
                extra={
                    "host": config.postgres_host,
                    "database": config.postgres_db,
                    "min_pool_size": config.postgres_min_pool_size,
                    "max_pool_size": config.postgres_max_pool_size,
                },
            )
        except psycopg2.Error as e:
            logger.exception(
                "Failed to initialize PostgreSQL connection pool",
                extra={"host": config.postgres_host, "error": str(e)},
            )
            raise PostgresPoolError(f"Failed to initialize PostgreSQL pool: {e}") from e

    @contextmanager
    def get_connection(self) -> Generator[PgConnection, None, None]:
        """Get a connection from the pool.

        Yields a connection and automatically releases it back to the pool
        when the context exits.

        Yields:
            Connection: PostgreSQL connection from the pool.

        Raises:
            PostgresPoolError: If connection checkout fails.

        Example:
            >>> pool = PostgresPool(config)
            >>> with pool.get_connection() as conn:
            ...     with conn.cursor() as cur:
            ...         cur.execute("SELECT 1")
            ...         result = cur.fetchone()
        """
        conn = None
        try:
            conn = self.pool.getconn()
            if conn is None:
                raise PostgresPoolError("Failed to get connection from pool")
            yield conn
        except psycopg2.Error as e:
            logger.exception("PostgreSQL connection error", extra={"error": str(e)})
            raise PostgresPoolError(f"PostgreSQL connection error: {e}") from e
        finally:
            if conn is not None:
                try:
                    self.pool.putconn(conn)
                except Exception as e:
                    logger.exception("Failed to release connection", extra={"error": str(e)})

    def close_all(self) -> None:
        """Close all connections in the pool.

        Safely closes all connections and cleans up resources.
        Safe to call even if pool is already closed.

        Example:
            >>> pool = PostgresPool(config)
            >>> # Use pool...
            >>> pool.close_all()
        """
        try:
            self.pool.closeall()
            logger.info(
                "PostgreSQL connection pool closed",
                extra={
                    "host": self._config.postgres_host,
                    "database": self._config.postgres_db,
                },
            )
        except Exception as e:
            logger.exception("Error closing PostgreSQL pool", extra={"error": str(e)})

    def __enter__(self) -> "PostgresPool":
        """Enter context manager (pool already initialized in __init__)."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit context manager and close all connections."""
        self.close_all()


# Export public API
__all__ = ["PostgresPool", "PostgresPoolError"]
