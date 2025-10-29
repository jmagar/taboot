"""Web document reader using Firecrawl API.

Implements web crawling via LlamaIndex FireCrawlWebReader.
Per research.md: Use LlamaIndex readers for standardized Document abstraction.
"""

import logging
import time

from llama_index.core import Document
from llama_index.readers.web import FireCrawlWebReader

from packages.common.config import get_config
from packages.common.resilience import resilient_external_call
from packages.ingest.url_filter import URLFilter

logger = logging.getLogger(__name__)


class WebReaderError(Exception):
    """Base exception for WebReader errors."""

    pass


class RateLimitError(WebReaderError):
    """Raised when rate limit is exceeded."""

    pass


class WebReader:
    """Web document reader using Firecrawl API.

    Implements rate limiting, error handling, robots.txt compliance, and URL path filtering.

    Path Filtering (Firecrawl v2):
    - include_paths: Whitelist regex patterns for URL paths to crawl
    - exclude_paths: Blacklist regex patterns for URL paths to skip (takes precedence)
    - Patterns match pathname only (e.g., "/en/docs" not "https://example.com/en/docs")
    - Configured via FIRECRAWL_INCLUDE_PATHS and FIRECRAWL_EXCLUDE_PATHS environment variables
    - Default: Blocks 17 common non-English language paths (de, fr, es, etc.)
    """

    def __init__(
        self,
        firecrawl_url: str,
        firecrawl_api_key: str,
        rate_limit_delay: float = 1.0,
        max_retries: int = 3,
    ) -> None:
        """Initialize WebReader with Firecrawl service URL.

        Args:
            firecrawl_url: URL of Firecrawl service (e.g., http://taboot-crawler:3002).
            firecrawl_api_key: API key for Firecrawl service.
            rate_limit_delay: Delay between requests in seconds (default: 1.0).
            max_retries: Maximum number of retry attempts (default: 3).
        """
        if not firecrawl_url:
            raise ValueError("firecrawl_url cannot be empty")
        if not firecrawl_api_key:
            raise ValueError("firecrawl_api_key cannot be empty")

        self.firecrawl_url = firecrawl_url
        self.firecrawl_api_key = firecrawl_api_key
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        self._last_request_time: float = 0.0

        # Load URL filter patterns from config
        config = get_config()
        self.include_paths = config.firecrawl_include_paths
        self.exclude_paths = config.firecrawl_exclude_paths

        # Parse comma-separated patterns into lists for client-side validation
        include_list = (
            [pattern.strip() for pattern in self.include_paths.split(",") if pattern.strip()]
            if self.include_paths
            else None
        )
        exclude_list = (
            [pattern.strip() for pattern in self.exclude_paths.split(",") if pattern.strip()]
            if self.exclude_paths
            else None
        )

        # Initialize URL filter for client-side validation (defense-in-depth)
        self.url_filter = URLFilter(
            include_patterns=include_list,
            exclude_patterns=exclude_list,
        )

        logger.info(
            f"Initialized WebReader (firecrawl_url={firecrawl_url}, "
            f"rate_limit_delay={rate_limit_delay}s, max_retries={max_retries}, "
            f"include_patterns={len(include_list) if include_list else 0}, "
            f"exclude_patterns={len(exclude_list) if exclude_list else 0})"
        )

    def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        self._last_request_time = time.time()

    @resilient_external_call(max_attempts=3, min_wait=1, max_wait=10)
    def _fetch_with_firecrawl(self, url: str, params: dict[str, object]) -> list[Document]:
        """Fetch documents from Firecrawl with retry logic.

        Args:
            url: URL to crawl.
            params: Firecrawl API parameters (snake_case - Firecrawl Python SDK format).

        Returns:
            list[Document]: List of LlamaIndex Document objects.

        Raises:
            Exception: If Firecrawl API call fails after retries.
        """
        logger.debug(f"Firecrawl params: {params}")

        # Create reader with crawl mode
        # Note: FireCrawlWebReader passes params to Firecrawl Python SDK which expects snake_case
        # The SDK internally converts to camelCase for the HTTP API
        reader = FireCrawlWebReader(
            api_key=self.firecrawl_api_key,
            api_url=self.firecrawl_url,
            mode="crawl",
            params=params,
        )

        docs = reader.load_data(url=url)

        # Add source_url to metadata if not already present
        # Firecrawl may return documents from different URLs during crawl
        for doc in docs:
            if not doc.metadata:
                doc.metadata = {}
            # Only set source_url if not already present (preserve actual crawled URLs)
            if "source_url" not in doc.metadata:
                doc.metadata["source_url"] = url

        return docs

    def load_data(self, url: str, limit: int | None = None) -> list[Document]:
        """Load documents from URL with optional limit.

        Args:
            url: URL to crawl (must start with http:// or https://).
            limit: Optional maximum number of pages to crawl.

        Returns:
            list[Document]: List of LlamaIndex Document objects with text and metadata.

        Raises:
            ValueError: If URL is invalid or empty.
            WebReaderError: If crawling fails after all retries.
        """
        if not url:
            raise ValueError("URL cannot be empty")

        if not url.startswith(("http://", "https://")):
            raise ValueError(f"Invalid URL: {url}")

        logger.info(f"Loading data from {url} (limit: {limit})")

        # Validate base URL against filters (defense-in-depth)
        is_allowed, reason = self.url_filter.validate_url(url)
        if not is_allowed:
            raise ValueError(
                f"URL rejected by filter: {reason}\n"
                f"Exclude patterns: {self.exclude_paths}\n"
                f"Include patterns: {self.include_paths}"
            )

        # Enforce rate limiting
        self._enforce_rate_limit()

        # Get locale config from environment (defaults to US/en-US)
        config = get_config()

        # Parse comma-separated languages into list
        languages = [lang.strip() for lang in config.firecrawl_default_languages.split(",")]

        # Build Firecrawl params with location parameter for language control
        # Per Firecrawl v2 API: location parameter prevents auto-redirects to non-English locales
        params: dict[str, object] = {
            "scrape_options": {
                "formats": ["markdown"],
                "location": {
                    "country": config.firecrawl_default_country,
                    "languages": languages,
                },
            }
        }
        if limit is not None:
            params["limit"] = limit

        # Build path filtering parameters (Firecrawl v2 URL filtering)
        # includePaths: Whitelist regex patterns for paths to crawl
        # excludePaths: Blacklist regex patterns for paths to skip (takes precedence)
        # Parse comma-separated config strings into lists, filtering empty strings
        include_paths: list[str] = [
            pattern.strip()
            for pattern in config.firecrawl_include_paths.split(",")
            if pattern.strip()
        ]
        exclude_paths: list[str] = [
            pattern.strip()
            for pattern in config.firecrawl_exclude_paths.split(",")
            if pattern.strip()
        ]

        # Add to params if non-empty
        if include_paths:
            params["include_paths"] = include_paths
        if exclude_paths:
            params["exclude_paths"] = exclude_paths

        try:
            docs = self._fetch_with_firecrawl(url, params)
            logger.info(f"Loaded {len(docs)} documents from {url}")

            # Post-crawl filtering: Filter returned documents by source URL
            # (defense-in-depth to catch documents that slipped through Firecrawl filtering)
            if docs:
                original_count = len(docs)
                allowed_docs = []
                for doc in docs:
                    doc_url = doc.metadata.get("source_url", "") if doc.metadata else ""
                    is_allowed, reason = self.url_filter.validate_url(doc_url)
                    if is_allowed:
                        allowed_docs.append(doc)
                    else:
                        logger.warning(f"Filtered document after crawl: {reason}")

                docs = allowed_docs
                if len(docs) < original_count:
                    logger.info(
                        f"Post-crawl filtering: {original_count - len(docs)} documents removed"
                    )

            return docs
        except Exception as e:
            logger.error(f"Failed to load {url}: {e}")
            raise WebReaderError(f"Failed to load {url}") from e
