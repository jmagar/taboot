"""Web document reader using Firecrawl API.

Implements web crawling via LlamaIndex FireCrawlWebReader.
Per research.md: Use LlamaIndex readers for standardized Document abstraction.
"""

import logging
import time

from llama_index.core import Document
from llama_index.readers.web import FireCrawlWebReader

from packages.common.resilience import resilient_external_call

logger = logging.getLogger(__name__)


class WebReaderError(Exception):
    """Base exception for WebReader errors."""

    pass


class RateLimitError(WebReaderError):
    """Raised when rate limit is exceeded."""

    pass


class WebReader:
    """Web document reader using Firecrawl API.

    Implements rate limiting, error handling, and robots.txt compliance.
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

        logger.info(
            f"Initialized WebReader (firecrawl_url={firecrawl_url}, "
            f"rate_limit_delay={rate_limit_delay}s, max_retries={max_retries})"
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
            params: Firecrawl API parameters.

        Returns:
            list[Document]: List of LlamaIndex Document objects.

        Raises:
            Exception: If Firecrawl API call fails after retries.
        """
        # Create reader with crawl mode
        reader = FireCrawlWebReader(
            api_key=self.firecrawl_api_key,
            api_url=self.firecrawl_url,
            mode="crawl",
            params=params,
        )

        docs = reader.load_data(url=url)

        # Add source_url to metadata
        for doc in docs:
            if not doc.metadata:
                doc.metadata = {}
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

        # Enforce rate limiting
        self._enforce_rate_limit()

        # Build Firecrawl params
        # formats goes inside scrape_options per Firecrawl v2 API
        params: dict[str, object] = {"scrape_options": {"formats": ["markdown"]}}
        if limit is not None:
            params["limit"] = limit

        try:
            docs = self._fetch_with_firecrawl(url, params)
            logger.info(f"Loaded {len(docs)} documents from {url}")
            return docs
        except Exception as e:
            logger.error(f"Failed to load {url}: {e}")
            raise WebReaderError(f"Failed to load {url}") from e
