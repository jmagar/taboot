"""Abstract base reader interface for data source ingestion.

This module provides the BaseReader abstract class that all data source readers must extend.
It implements common functionality for:
1. State management (cursor tracking via Redis)
2. Configuration retrieval from config.yaml
3. Credential validation
4. Logging with source context

Each reader subclass must implement:
- load_data() -> list[Document]: Load documents from the data source
- supports_incremental_sync() -> bool: Whether source supports incremental sync
"""

import os
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from llamacrawl.models.document import Document
from llamacrawl.storage.redis import RedisClient
from llamacrawl.utils.logging import get_logger


class BaseReader(ABC):
    """Abstract base class for all data source readers.

    This class provides common functionality for data ingestion including:
    - Cursor-based incremental sync state management via Redis
    - Source-specific configuration retrieval
    - Credential validation
    - Logging with source context

    Subclasses must implement load_data() and supports_incremental_sync().

    Attributes:
        source_name: Name of the data source (e.g., 'firecrawl', 'github')
        config: Source-specific configuration dictionary
        redis_client: Redis client for state management
        logger: Logger instance with source context
    """

    def __init__(
        self,
        source_name: str,
        config: dict[str, Any],
        redis_client: RedisClient,
    ):
        """Initialize the base reader.

        Args:
            source_name: Name of the data source (e.g., 'firecrawl', 'github', 'reddit')
            config: Source-specific configuration from config.yaml
            redis_client: Redis client instance for state management

        Raises:
            ValueError: If source_name is empty or invalid
        """
        if not source_name:
            raise ValueError("source_name cannot be empty")

        self.source_name = source_name
        self.config = config
        self.redis_client = redis_client

        # Create logger with source context
        self.logger = get_logger(f"llamacrawl.readers.{source_name}")
        self.logger.info(
            f"Initialized {self.__class__.__name__} for source '{source_name}'",
            extra={"source": source_name},
        )

    # =========================================================================
    # Abstract Methods (must be implemented by subclasses)
    # =========================================================================

    @abstractmethod
    def load_data(
        self,
        progress_callback: Callable[[int, int], None] | None = None,
        **kwargs: Any,
    ) -> list[Document]:
        """Load documents from the data source.

        This method must be implemented by each reader subclass to fetch data from
        the specific data source and convert it to Document objects.

        For sources that support incremental sync, implementations should:
        1. Call get_last_cursor() to retrieve the last sync position
        2. Fetch only new/updated documents since the cursor
        3. Call set_last_cursor() after successful ingestion

        Args:
            progress_callback: Optional callback(current, total) for progress updates.
                             Should be called periodically during loading to report progress.
            **kwargs: Reader-specific parameters (e.g., url, query, filters)

        Returns:
            List of Document objects loaded from the source

        Raises:
            Exception: Various exceptions depending on data source (auth errors,
                      network errors, API errors, etc.)

        Example:
            >>> def on_progress(current: int, total: int) -> None:
            ...     print(f"Progress: {current}/{total}")
            >>> reader = FirecrawlReader(source_name='firecrawl', config=cfg, redis_client=redis)
            >>> documents = reader.load_data(url='https://example.com', progress_callback=on_progress)
            >>> print(f"Loaded {len(documents)} documents")
        """
        pass

    @abstractmethod
    def supports_incremental_sync(self) -> bool:
        """Check if this reader supports incremental synchronization.

        Returns:
            True if the reader can fetch only new/changed documents using cursors,
            False if it must refetch all data on each sync.

        Example:
            >>> reader = GitHubReader(...)
            >>> if reader.supports_incremental_sync():
            ...     print("This reader supports efficient incremental updates")
        """
        pass

    # =========================================================================
    # Common Methods (implemented in base class)
    # =========================================================================

    def get_last_cursor(self) -> str | None:
        """Retrieve the last sync cursor from Redis.

        The cursor represents the last synchronization point and can be:
        - Timestamp (ISO 8601 format): '2024-09-30T10:00:00Z'
        - API-specific cursor: historyId, page token, etc.
        - Custom identifier: last processed item ID

        Returns:
            Cursor value as string, or None if no previous sync

        Example:
            >>> cursor = reader.get_last_cursor()
            >>> if cursor:
            ...     # Use cursor to fetch only new data
            ...     documents = fetch_since(cursor)
            ... else:
            ...     # First sync - fetch all data
            ...     documents = fetch_all()
        """
        cursor = self.redis_client.get_cursor(self.source_name)
        if cursor:
            self.logger.debug(
                f"Retrieved cursor for {self.source_name}: {cursor}",
                extra={"source": self.source_name, "cursor": cursor},
            )
        else:
            self.logger.debug(
                f"No previous cursor found for {self.source_name} (first sync)",
                extra={"source": self.source_name},
            )
        return cursor

    def set_last_cursor(self, cursor: str) -> None:
        """Store the last sync cursor in Redis.

        This should be called after successful document ingestion to mark the
        sync position for the next incremental sync.

        Args:
            cursor: Cursor value to store (timestamp, token, ID, etc.)

        Example:
            >>> # After successfully ingesting documents
            >>> latest_timestamp = documents[-1].metadata.timestamp.isoformat()
            >>> reader.set_last_cursor(latest_timestamp)
        """
        self.redis_client.set_cursor(self.source_name, cursor)
        self.logger.info(
            f"Updated cursor for {self.source_name}: {cursor}",
            extra={"source": self.source_name, "cursor": cursor},
        )

    def get_source_config(self) -> dict[str, Any]:
        """Get source-specific configuration from config.yaml.

        Returns:
            Dictionary containing source-specific configuration settings.
            Returns the config dictionary passed during initialization.

        Example:
            >>> config = reader.get_source_config()
            >>> max_pages = config.get('max_pages', 1000)
            >>> enabled = config.get('enabled', True)
        """
        return self.config

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def validate_credentials(self, required_env_vars: list[str]) -> None:
        """Validate that required environment variables are set.

        This method should be called in subclass constructors to fail fast
        if required credentials are missing.

        Args:
            required_env_vars: List of required environment variable names

        Raises:
            ValueError: If any required environment variable is missing or empty

        Example:
            >>> # In FirecrawlReader.__init__
            >>> self.validate_credentials(['FIRECRAWL_API_KEY', 'FIRECRAWL_API_URL'])
        """
        missing_vars = []
        empty_vars = []

        for var in required_env_vars:
            value = os.environ.get(var)
            if value is None:
                missing_vars.append(var)
            elif not value.strip():
                empty_vars.append(var)

        errors = []
        if missing_vars:
            errors.append(f"Missing required environment variables: {', '.join(missing_vars)}")
        if empty_vars:
            errors.append(f"Empty environment variables: {', '.join(empty_vars)}")

        if errors:
            error_message = " | ".join(errors)
            self.logger.error(
                f"Credential validation failed for {self.source_name}: {error_message}",
                extra={
                    "source": self.source_name,
                    "missing_vars": missing_vars,
                    "empty_vars": empty_vars,
                },
            )
            raise ValueError(f"Credential validation failed: {error_message}")

        self.logger.debug(
            f"Credentials validated successfully for {self.source_name}",
            extra={"source": self.source_name, "validated_vars": required_env_vars},
        )

    def get_api_client(self) -> Any:
        """Lazy initialization of API client.

        Subclasses should override this method to provide lazy initialization
        of their specific API clients. This allows credential validation to
        happen early while deferring expensive client initialization until needed.

        Returns:
            API client instance specific to the data source

        Raises:
            NotImplementedError: If subclass doesn't override this method

        Example:
            >>> # In GitHubReader
            >>> def get_api_client(self) -> Github:
            ...     if not hasattr(self, '_client'):
            ...         self._client = Github(os.environ['GITHUB_TOKEN'])
            ...     return self._client
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement get_api_client() "
            "for lazy client initialization"
        )

    def log_load_summary(
        self,
        total_fetched: int,
        filtered_count: int = 0,
        error_count: int = 0,
        **extra_fields: Any,
    ) -> None:
        """Log a summary of the load operation.

        Helper method for consistent logging of load operation results.

        Args:
            total_fetched: Total number of documents fetched from source
            filtered_count: Number of documents filtered out (e.g., duplicates)
            error_count: Number of documents that failed to process
            **extra_fields: Additional fields to include in log context

        Example:
            >>> reader.log_load_summary(
            ...     total_fetched=150,
            ...     filtered_count=10,
            ...     error_count=2,
            ...     cursor_used='2024-09-30T10:00:00Z'
            ... )
        """
        log_extra = {
            "source": self.source_name,
            "total_fetched": total_fetched,
            "filtered_count": filtered_count,
            "error_count": error_count,
            "returned_count": total_fetched - filtered_count - error_count,
            **extra_fields,
        }

        self.logger.info(
            f"Load complete for {self.source_name}: "
            f"{total_fetched} fetched, {filtered_count} filtered, "
            f"{error_count} errors, {log_extra['returned_count']} returned",
            extra=log_extra,
        )
