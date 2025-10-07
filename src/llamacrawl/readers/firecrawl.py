"""Firecrawl web scraping reader for LlamaCrawl.

This module provides the FirecrawlReader class for ingesting web content via
Firecrawl's v2 API. It supports multiple modes:
- scrape: Single URL scraping
- crawl: Full site crawling with configurable depth
- map: URL discovery from sitemaps
- extract: AI-powered structured data extraction

The reader uses LlamaIndex's FireCrawlWebReader internally (which now supports
Firecrawl v2 SDK as of PR #19773) and converts results to our Document model.
"""

import hashlib
import os
from datetime import UTC, datetime
from typing import Any, Literal
from urllib.parse import urlparse

from llama_index.readers.web import FireCrawlWebReader

from llamacrawl.models.document import Document, DocumentMetadata
from llamacrawl.readers.base import BaseReader
from llamacrawl.storage.redis import RedisClient
from llamacrawl.utils.retry import retry_with_backoff


class FirecrawlReader(BaseReader):
    """Firecrawl web scraping reader.

    This reader uses Firecrawl's v2 API to scrape, crawl, map, or extract data
    from websites. It extends BaseReader to provide consistent interface and
    state management.

    Attributes:
        source_name: Name of the data source (should be 'firecrawl')
        config: Firecrawl-specific configuration from config.yaml
        redis_client: Redis client for state management
        api_url: Firecrawl API URL from environment
        api_key: Firecrawl API key from environment
        firecrawl_reader: Internal LlamaIndex FireCrawlWebReader instance

    Example:
        >>> reader = FirecrawlReader(
        ...     source_name='firecrawl',
        ...     config={'max_pages': 1000, 'default_crawl_depth': 3},
        ...     redis_client=redis
        ... )
        >>> documents = reader.load_data(
        ...     url='https://example.com',
        ...     mode='crawl'
        ... )
    """

    ALLOWED_METADATA_KEYS = {
        "title",
        "description",
        "language",
        "keywords",
        "ogTitle",
        "ogDescription",
        "ogImage",
        "status_code",
        "content_type",
    }

    def __init__(
        self,
        source_name: str,
        config: dict[str, Any],
        redis_client: RedisClient,
    ):
        """Initialize Firecrawl reader.

        Args:
            source_name: Name of the data source (should be 'firecrawl')
            config: Firecrawl-specific configuration from config.yaml
            redis_client: Redis client instance

        Raises:
            ValueError: If required environment variables are missing or invalid
        """
        super().__init__(source_name, config, redis_client)

        # Validate required environment variables
        self.validate_credentials(["FIRECRAWL_API_URL", "FIRECRAWL_API_KEY"])

        # Store API credentials
        self.api_url = os.environ["FIRECRAWL_API_URL"]
        self.api_key = os.environ["FIRECRAWL_API_KEY"]

        # Validate API key format (should not be example placeholder)
        if self.api_key.startswith("fc-xxx"):
            raise ValueError(
                "Invalid FIRECRAWL_API_KEY. Please set a valid API key in .env file. "
                "Get your API key from your Firecrawl instance admin panel."
            )

        self.include_paths: list[str] = config.get("include_paths", []) or []
        self.exclude_paths: list[str] = config.get("exclude_paths", []) or []
        self.concurrency: int | None = config.get("concurrency")
        self.max_retries: int | None = config.get("max_retries")
        self.retry_delay_ms: int | None = config.get("retry_delay_ms")
        self.timeout_ms: int | None = config.get("timeout_ms")
        self.max_metadata_chars: int = config.get("metadata_max_chars", 256)
        self.max_metadata_list_items: int = config.get("metadata_max_list_items", 5)
        self.max_metadata_dict_items: int = config.get("metadata_max_dict_items", 5)

        self._base_params = self._build_base_params()

        # Initialize LlamaIndex FireCrawlWebReader
        # Note: FireCrawlWebReader now supports Firecrawl v2 SDK (as of PR #19773)
        self.firecrawl_reader = FireCrawlWebReader(
            api_key=self.api_key,
            api_url=self.api_url,
            params=self._base_params,
        )

        self.logger.info(
            f"FirecrawlReader initialized with API URL: {self.api_url}",
            extra={"source": self.source_name, "api_url": self.api_url},
        )

    def _build_base_params(self) -> dict[str, Any]:
        """Build base parameters applied to every Firecrawl request."""
        params: dict[str, Any] = {}

        if self.include_paths:
            params["includePaths"] = self.include_paths
        if self.exclude_paths:
            params["excludePaths"] = self.exclude_paths
        if self.concurrency is not None:
            params["concurrency"] = self.concurrency
        if self.max_retries is not None:
            params["maxRetries"] = self.max_retries
        if self.retry_delay_ms is not None:
            params["retryDelay"] = self.retry_delay_ms
        if self.timeout_ms is not None:
            params["timeout"] = self.timeout_ms

        return params

    def supports_incremental_sync(self) -> bool:
        """Check if Firecrawl supports incremental synchronization.

        Returns:
            False - Firecrawl does not support incremental sync.
                   Each crawl fetches the entire website from scratch.
        """
        return False

    def load_data(
        self,
        url: str | list[str] | None = None,
        mode: Literal["scrape", "crawl", "map", "extract"] = "scrape",
        limit: int | None = None,
        max_depth: int | None = None,
        formats: list[str] | None = None,
        **kwargs: Any,
    ) -> list[Document]:
        """Load documents from Firecrawl.

        This method fetches web content via Firecrawl and converts it to Document
        objects with proper metadata. Supports multiple modes:
        - scrape: Single URL scraping
        - crawl: Full site crawling
        - map: URL discovery
        - extract: Structured data extraction

        Args:
            url: URL(s) to scrape/crawl. If None, uses URLs from config.
            mode: Firecrawl mode (scrape/crawl/map/extract). Default: scrape
            limit: Maximum number of pages to fetch (max_pages parameter).
                  Default from config or 1000.
            max_depth: Maximum crawl depth for crawl mode (maxDepth parameter).
                      Default from config or 3. Only used in crawl mode.
            formats: Output formats (markdown, html). Default: ['markdown']
            **kwargs: Additional Firecrawl API parameters

        Returns:
            List of Document objects with web content

        Raises:
            ValueError: If URL is invalid or mode is unsupported
            ConnectionError: If Firecrawl API is unreachable
            Exception: Various Firecrawl API errors

        Example:
            >>> # Single URL scraping
            >>> docs = reader.load_data(url='https://example.com', mode='scrape')
            >>> # Full site crawling with depth limit
            >>> docs = reader.load_data(
            ...     url='https://example.com',
            ...     mode='crawl',
            ...     limit=100,
            ...     max_depth=2
            ... )
        """
        # Determine URL(s) to process
        urls_to_process: list[str] = []

        if url is None:
            # Use URLs from config
            config_urls = self.config.get("urls", [])
            if not config_urls:
                raise ValueError(
                    "No URLs provided. Either pass url parameter or configure "
                    "sources.firecrawl.urls in config.yaml"
                )
            urls_to_process = config_urls
        elif isinstance(url, str):
            urls_to_process = [url]
        else:
            urls_to_process = url

        # Validate URLs
        for url_str in urls_to_process:
            if not self._validate_url(url_str):
                raise ValueError(f"Invalid URL: {url_str}")

        # Get configuration parameters
        limit = limit or self.config.get("max_pages", 1000)
        max_depth = max_depth or self.config.get("default_crawl_depth", 3)
        formats = formats or self.config.get("formats", ["markdown"])

        self.logger.info(
            f"Loading data from {len(urls_to_process)} URL(s) in {mode} mode",
            extra={
                "source": self.source_name,
                "mode": mode,
                "url_count": len(urls_to_process),
                "limit": limit,
                "max_depth": max_depth if mode == "crawl" else None,
            },
        )

        # Process each URL and collect documents
        all_documents: list[Document] = []

        for url_str in urls_to_process:
            try:
                documents = self._load_single_url(
                    url=url_str,
                    mode=mode,
                    limit=limit,
                    max_depth=max_depth,
                    formats=formats,
                    **kwargs,
                )
                all_documents.extend(documents)

                self.logger.info(
                    f"Loaded {len(documents)} documents from {url_str}",
                    extra={
                        "source": self.source_name,
                        "url": url_str,
                        "document_count": len(documents),
                    },
                )

            except Exception as e:
                self.logger.error(
                    f"Failed to load URL {url_str}: {e}",
                    extra={
                        "source": self.source_name,
                        "url": url_str,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
                # Continue processing other URLs
                continue

        # Log summary
        self.log_load_summary(
            total_fetched=len(all_documents),
            filtered_count=0,
            error_count=0,
            mode=mode,
            url_count=len(urls_to_process),
        )

        return all_documents

    @retry_with_backoff(max_attempts=3, initial_delay=2.0, max_delay=60.0)
    def _load_single_url(
        self,
        url: str,
        mode: Literal["scrape", "crawl", "map", "extract"],
        limit: int,
        max_depth: int,
        formats: list[str],
        **kwargs: Any,
    ) -> list[Document]:
        """Load documents from a single URL with retry logic.

        This internal method handles the actual Firecrawl API call with retry
        logic for rate limits and transient failures.

        Args:
            url: URL to scrape/crawl
            mode: Firecrawl mode
            limit: Max pages
            max_depth: Max crawl depth (for crawl mode)
            formats: Output formats
            **kwargs: Additional API parameters

        Returns:
            List of Document objects
        """
        # Build Firecrawl parameters based on mode
        params = self._build_firecrawl_params(
            mode=mode,
            limit=limit,
            max_depth=max_depth,
            formats=formats,
            **kwargs,
        )

        # Create a FireCrawlWebReader instance with the specific mode and params
        # Note: FireCrawlWebReader requires mode and params at initialization, not in load_data()
        reader_instance = FireCrawlWebReader(
            api_key=self.api_key,
            api_url=self.api_url,
            mode=mode,
            params=params,
        )

        # Call load_data() with just the URL (load_data only accepts url/query/urls)
        llamaindex_docs = reader_instance.load_data(url=url)

        # Convert LlamaIndex documents to our Document model
        documents = self._convert_to_documents(llamaindex_docs, source_url=url)

        return documents

    def _build_firecrawl_params(
        self,
        mode: Literal["scrape", "crawl", "map", "extract"],
        limit: int,
        max_depth: int,
        formats: list[str],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Build Firecrawl API parameters based on mode.

        Args:
            mode: Firecrawl mode
            limit: Max pages
            max_depth: Max crawl depth
            formats: Output formats
            **kwargs: Additional parameters

        Returns:
            Dictionary of Firecrawl API parameters
        """
        params: dict[str, Any] = self._base_params.copy()

        # Mode-specific parameters
        if mode == "crawl":
            # Crawl mode: nest scrape options in scrape_options parameter
            if formats:
                scrape_options = params.get("scrape_options", {})
                scrape_options["formats"] = formats
                params["scrape_options"] = scrape_options
            params["limit"] = limit
            params["maxDepth"] = max_depth

        elif mode == "scrape":
            # Scrape mode: formats at top level
            if formats:
                params["formats"] = formats

        elif mode == "map":
            # Map mode uses limit for URL discovery (no content fetching, so no formats)
            params["limit"] = limit

        elif mode == "extract":
            # Extract mode might have schema or prompt
            if "schema" in kwargs:
                params["schema"] = kwargs["schema"]
            if "prompt" in kwargs:
                params["prompt"] = kwargs["prompt"]
            if formats:
                params["formats"] = formats

        # Merge any additional kwargs
        for key, value in kwargs.items():
            if key not in ("schema", "prompt"):  # Already handled above
                params[key] = value

        return params

    def _convert_to_documents(
        self, llamaindex_docs: list[Any], source_url: str
    ) -> list[Document]:
        """Convert LlamaIndex documents to our Document model.

        Args:
            llamaindex_docs: List of LlamaIndex Document objects
            source_url: Original source URL

        Returns:
            List of our Document objects with proper metadata
        """
        documents: list[Document] = []
        timestamp = datetime.now(UTC)

        for idx, llama_doc in enumerate(llamaindex_docs):
            # Extract content and metadata
            content = llama_doc.text or llama_doc.get_content()
            llama_metadata = llama_doc.metadata or {}
            sanitized_metadata = self._sanitize_firecrawl_metadata(llama_metadata)

            # Generate unique document ID
            # Use URL from metadata if available, otherwise use source_url
            doc_url = llama_metadata.get("url", source_url)
            doc_id = self._generate_doc_id(doc_url, idx)

            # Compute content hash for deduplication
            content_hash = self._compute_content_hash(content)

            # Extract title (try multiple sources)
            title = (
                llama_metadata.get("title")
                or llama_metadata.get("ogTitle")
                or self._extract_title_from_url(doc_url)
            )

            # Build metadata
            metadata = DocumentMetadata(
                source_type="firecrawl",
                source_url=doc_url,
                timestamp=timestamp,
                extra={
                    "firecrawl_metadata": sanitized_metadata,
                    "index": idx,
                    "total_docs": len(llamaindex_docs),
                },
            )

            # Create Document
            document = Document(
                doc_id=doc_id,
                title=title,
                content=content,
                content_hash=content_hash,
                metadata=metadata,
                embedding=None,  # Embeddings are generated during ingestion
            )

            documents.append(document)

        return documents

    def _sanitize_firecrawl_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """Reduce Firecrawl metadata to a compact subset to avoid oversized chunks."""
        sanitized: dict[str, Any] = {}
        if not isinstance(metadata, dict):
            return sanitized

        for key in self.ALLOWED_METADATA_KEYS:
            if key in metadata and metadata[key] not in (None, "", [], {}):
                sanitized[key] = self._truncate_metadata_value(metadata[key])

        return sanitized

    def _truncate_metadata_value(self, value: Any, depth: int = 0) -> Any:
        """Truncate metadata values to keep payload sizes manageable."""
        if isinstance(value, str):
            if len(value) > self.max_metadata_chars:
                return value[: self.max_metadata_chars] + "..."
            return value
        if isinstance(value, (int, float, bool)) or value is None:
            return value
        if isinstance(value, list):
            truncated_items = [
                self._truncate_metadata_value(item, depth + 1)
                for item in value[: self.max_metadata_list_items]
            ]
            return truncated_items
        if isinstance(value, dict):
            truncated_dict: dict[str, Any] = {}
            for idx, (k, v) in enumerate(value.items()):
                if idx >= self.max_metadata_dict_items:
                    break
                truncated_dict[k] = self._truncate_metadata_value(v, depth + 1)
            return truncated_dict
        return str(value)[: self.max_metadata_chars]

    def _validate_url(self, url: str) -> bool:
        """Validate URL format.

        Args:
            url: URL string to validate

        Returns:
            True if URL is valid, False otherwise
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def _generate_doc_id(self, url: str, index: int) -> str:
        """Generate unique document ID.

        Args:
            url: Source URL
            index: Document index within batch

        Returns:
            Unique document ID string
        """
        # Use URL hash + index to ensure uniqueness
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        return f"firecrawl_{url_hash}_{index}"

    def _compute_content_hash(self, content: str) -> str:
        """Compute SHA-256 hash of normalized content.

        Args:
            content: Document content

        Returns:
            SHA-256 hash as hex string
        """
        # Normalize content: strip whitespace, lowercase
        normalized = content.strip().lower()

        # Compute SHA-256 hash
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _extract_title_from_url(self, url: str) -> str:
        """Extract title from URL as fallback.

        Args:
            url: Source URL

        Returns:
            Title extracted from URL path
        """
        try:
            parsed = urlparse(url)
            path = parsed.path.strip("/")

            if path:
                # Use last path segment as title
                segments = path.split("/")
                title = segments[-1].replace("-", " ").replace("_", " ").title()
                return title
            else:
                # Use domain as title
                return parsed.netloc

        except Exception:
            return url

    def get_api_client(self) -> FireCrawlWebReader:
        """Get the FireCrawlWebReader instance.

        Returns:
            The internal FireCrawlWebReader instance
        """
        return self.firecrawl_reader
