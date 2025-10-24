"""Web document reader using Firecrawl API.

Implements web crawling via LlamaIndex FireCrawlWebReader.
Per research.md: Use LlamaIndex readers for standardized Document abstraction.
"""

import logging
import time

from llama_index.core import Document
from llama_index.readers.web import FireCrawlWebReader

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

        # Create reader with crawl mode
        reader = FireCrawlWebReader(
            api_key=self.firecrawl_api_key,
            api_url=self.firecrawl_url,
            mode="crawl",
            params=params,
        )

        # Retry logic with exponential backoff
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                docs = reader.load_data(url=url)

                # Add source_url to metadata
                for doc in docs:
                    if not doc.metadata:
                        doc.metadata = {}
                    doc.metadata["source_url"] = url

                logger.info(f"Loaded {len(docs)} documents from {url}")
                return docs

            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    backoff = 2**attempt
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.max_retries} failed for {url}: {e}. "
                        f"Retrying in {backoff}s..."
                    )
                    time.sleep(backoff)
                else:
                    logger.error(f"All {self.max_retries} attempts failed for {url}: {e}")

        # All retries exhausted
        raise WebReaderError(
            f"Failed to load {url} after {self.max_retries} attempts"
        ) from last_error
