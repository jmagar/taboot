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

import asyncio
import hashlib
import math
import os
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Literal
from urllib.parse import urlparse

from firecrawl import AsyncFirecrawl
from firecrawl.v2.watcher_async import AsyncWatcher
from llama_index.readers.web import FireCrawlWebReader

from llamacrawl.models.document import Document, DocumentMetadata
from llamacrawl.readers.base import BaseReader
from llamacrawl.storage.redis import RedisClient
from llamacrawl.utils.retry import async_retry_with_backoff, retry_with_backoff


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
        self.cache_max_age_ms: int | None = config.get("cache_max_age_ms", 172800000)
        self.location: dict[str, Any] | None = config.get("location")
        self.filter_non_english_metadata: bool = config.get("filter_non_english_metadata", True)
        self.max_concurrency: int | None = config.get("max_concurrency", config.get("concurrency"))
        self.max_retries: int | None = config.get("max_retries")
        self.retry_delay_ms: int | None = config.get("retry_delay_ms")
        self.crawl_delay_ms: int | None = config.get("crawl_delay_ms")
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

        # Initialize async Firecrawl client for websocket-enabled workflows
        self.async_firecrawl_client = AsyncFirecrawl(
            api_key=self.api_key,
            api_url=self.api_url,
        )

        self.logger.info(
            f"FirecrawlReader initialized with API URL: {self.api_url}",
            extra={"source": self.source_name, "api_url": self.api_url},
        )

    def _build_base_params(self) -> dict[str, Any]:
        """Build base parameters applied to every Firecrawl request."""
        params: dict[str, Any] = {}
        if self.timeout_ms is not None:
            params["timeout"] = self.timeout_ms
        params["integration"] = "llamaindex"
        return params

    def supports_incremental_sync(self) -> bool:
        """Check if Firecrawl supports incremental synchronization.

        Returns:
            False - Firecrawl does not support incremental sync.
                   Each crawl fetches the entire website from scratch.
        """
        return False

    def _resolve_urls(self, url: str | list[str] | None) -> list[str]:
        """Normalize url parameter into a list of URLs."""
        if url is None:
            config_urls = self.config.get("urls", [])
            if not config_urls:
                raise ValueError(
                    "No URLs provided. Either pass url parameter or configure "
                    "sources.firecrawl.urls in config.yaml"
                )
            return config_urls

        if isinstance(url, str):
            return [url]

        return url

    def _ensure_url_allowed(self, url: str, mode: str) -> None:
        """Validate URL against exclude patterns when applicable."""
        if mode == "crawl" or not self.exclude_paths:
            return

        import re

        parsed = urlparse(url)
        path = parsed.path
        for pattern in self.exclude_paths:
            if pattern.startswith("^"):
                try:
                    if re.search(pattern, path):
                        raise ValueError(
                            f"URL path '{path}' matches exclude pattern '{pattern}'. "
                            "This URL is excluded by your configuration."
                        )
                except re.error:
                    continue
            else:
                pattern_normalized = pattern.strip("*").strip("/")
                if pattern_normalized and pattern_normalized in path.split("/"):
                    raise ValueError(
                        f"URL path '{path}' matches exclude pattern '{pattern}'. "
                        "This URL is excluded by your configuration."
                    )

    def load_data(
        self,
        progress_callback: Callable[[int, int], None] | None = None,
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
        urls_to_process = self._resolve_urls(url)

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

    async def aload_data(
        self,
        progress_callback: Callable[[int, int | None, str], None] | None = None,
        url: str | list[str] | None = None,
        mode: Literal["scrape", "crawl", "map", "extract"] = "scrape",
        limit: int | None = None,
        max_depth: int | None = None,
        formats: list[str] | None = None,
        **kwargs: Any,
    ) -> list[Document]:
        """Asynchronously load documents from Firecrawl using the AsyncFirecrawl SDK."""
        urls_to_process = self._resolve_urls(url)

        for url_str in urls_to_process:
            if not self._validate_url(url_str):
                raise ValueError(f"Invalid URL: {url_str}")

        # Get configuration parameters
        limit = limit or self.config.get("max_pages", 1000)
        max_depth = max_depth or self.config.get("default_crawl_depth", 3)
        formats = formats or self.config.get("formats", ["markdown"])

        self.logger.info(
            f"Asynchronously loading data from {len(urls_to_process)} URL(s) in {mode} mode",
            extra={
                "source": self.source_name,
                "mode": mode,
                "url_count": len(urls_to_process),
                "limit": limit,
                "max_depth": max_depth if mode == "crawl" else None,
            },
        )

        all_documents: list[Document] = []
        error_count = 0

        for url_str in urls_to_process:
            try:
                documents = await self._aload_single_url(
                    url=url_str,
                    mode=mode,
                    limit=limit,
                    max_depth=max_depth,
                    formats=formats,
                    progress_callback=progress_callback,
                    **kwargs,
                )

                all_documents.extend(documents)

                self.logger.info(
                    f"Asynchronously loaded {len(documents)} documents from {url_str}",
                    extra={
                        "source": self.source_name,
                        "url": url_str,
                        "document_count": len(documents),
                        "mode": mode,
                    },
                )

            except Exception as e:
                error_count += 1
                self.logger.error(
                    f"Failed to asynchronously load URL {url_str}: {e}",
                    extra={
                        "source": self.source_name,
                        "url": url_str,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "mode": mode,
                    },
                )
                continue

        self.log_load_summary(
            total_fetched=len(all_documents),
            filtered_count=0,
            error_count=error_count,
            mode=mode,
            url_count=len(urls_to_process),
            async_mode=True,
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

        Raises:
            ValueError: If URL matches exclude_paths pattern
        """
        # Validate URL against exclude_paths for applicable modes
        self._ensure_url_allowed(url, mode)

        # Build Firecrawl parameters based on mode
        params = self._build_firecrawl_params(
            mode=mode,
            limit=limit,
            max_depth=max_depth,
            formats=formats,
            **kwargs,
        )

        self.logger.info(
            f"Creating FireCrawlWebReader for {mode} mode",
            extra={"url": url, "mode": mode, "params": params},
        )

        if mode == "crawl":
            return self._run_sync_crawl_with_watcher(url=url, params=params)

        # Create a FireCrawlWebReader instance with the specific mode and params
        # Note: FireCrawlWebReader requires mode and params at initialization, not in load_data()
        reader_instance = FireCrawlWebReader(
            api_key=self.api_key,
            api_url=self.api_url,
            mode=mode,
            params=params,
        )

        self.logger.debug(f"Calling load_data() for {url}")
        # Call load_data() with just the URL (load_data only accepts url/query/urls)
        llamaindex_docs = reader_instance.load_data(url=url)

        self.logger.debug(f"Loaded {len(llamaindex_docs)} documents from {url}")

        # Convert LlamaIndex documents to our Document model
        documents = self._convert_to_documents(llamaindex_docs, source_url=url)

        return documents

    @async_retry_with_backoff(max_attempts=3, initial_delay=2.0, max_delay=60.0)
    async def _aload_single_url(
        self,
        url: str,
        mode: Literal["scrape", "crawl", "map", "extract"],
        limit: int,
        max_depth: int,
        formats: list[str],
        progress_callback: Callable[[int, int | None, str], None] | None = None,
        **kwargs: Any,
    ) -> list[Document]:
        """Async variant of _load_single_url using the official AsyncFirecrawl SDK."""
        self._ensure_url_allowed(url, mode)

        params = self._build_firecrawl_params(
            mode=mode,
            limit=limit,
            max_depth=max_depth,
            formats=formats,
            **kwargs,
        )

        if mode == "crawl":
            return await self._async_crawl_with_watcher(
                url=url,
                params=params,
                progress_callback=progress_callback,
            )

        # For other modes, run the synchronous loader in a worker thread
        return await asyncio.to_thread(
            self._load_single_url,
            url,
            mode,
            limit,
            max_depth,
            formats,
            **kwargs,
        )

    async def _async_crawl_with_polling(
        self,
        *,
        url: str,
        params: dict[str, Any],
        progress_callback: Callable[[int, int | None, str], None] | None = None,
    ) -> list[Document]:
        """Run a Firecrawl crawl using periodic HTTP polling."""
        request_kwargs = self._prepare_async_crawl_params(params)

        self.logger.info(
            "Starting async Firecrawl crawl job",
            extra={
                "url": url,
                "params": request_kwargs,
            },
        )

        start_response = await self.async_firecrawl_client.start_crawl(url=url, **request_kwargs)
        job_id = getattr(start_response, "id", None) or start_response.get("id")  # type: ignore[union-attr]
        if not job_id:
            raise RuntimeError("Failed to start Firecrawl crawl job (missing job ID)")

        timeout_seconds = math.ceil(self.timeout_ms / 1000) if self.timeout_ms else None
        poll_interval = max(params.get("delay", 0) / 1000 if params.get("delay") else 2, 1)
        start_time = asyncio.get_event_loop().time()

        collected_docs: list[Any] = []
        status: str = "discovering"
        completed_count = 0
        total_count: int | None = None

        while True:
            try:
                response = await self.async_firecrawl_client._v2_client.async_http_client.get(
                    f"/v2/crawl/{job_id}"
                )
                body = response.json()
            except Exception as exc:  # pragma: no cover - defensive
                self.logger.warning(
                    "Failed to poll Firecrawl crawl status",
                    extra={"job_id": job_id, "error": str(exc)},
                )
                await asyncio.sleep(poll_interval)
                continue

            status = body.get("status", status)
            completed_count = body.get("completed", completed_count) or 0
            total_count = body.get("total", total_count)
            docs = body.get("data", []) or []

            self.logger.debug(
                "Firecrawl crawl poll",
                extra={
                    "job_id": job_id,
                    "status": status,
                    "completed": completed_count,
                    "total": total_count,
                    "docs": len(docs),
                },
            )

            # Accumulate documents (Firecrawl returns all docs in 'data' field)
            if docs:
                collected_docs = docs
                print(f"[POLLING DEBUG] Got {len(docs)} docs, status={status}")

            if progress_callback:
                progress_callback(completed_count, total_count, status)

            if status in {"completed", "failed", "cancelled"}:
                break

            if timeout_seconds is not None:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= timeout_seconds:
                    raise TimeoutError(
                        f"Firecrawl crawl timed out after {timeout_seconds} seconds"
                    )

            await asyncio.sleep(poll_interval)

        if status == "failed":
            raise RuntimeError(
                f"Firecrawl crawl job {job_id} failed to complete successfully"
            )

        print(f"[POLLING DEBUG] Completed with {len(collected_docs)} docs")
        print(f"[POLLING DEBUG] Doc types: {[type(d).__name__ for d in collected_docs[:3]] if collected_docs else 'NONE'}")

        self.logger.info(
            "Async Firecrawl crawl completed via polling",
            extra={
                "job_id": job_id,
                "document_count": len(collected_docs),
                "doc_types": [type(d).__name__ for d in collected_docs[:3]] if collected_docs else [],
            },
        )

        return self._convert_to_documents(collected_docs, source_url=url)

    async def _async_crawl_with_watcher(
        self,
        *,
        url: str,
        params: dict[str, Any],
        progress_callback: Callable[[int, int | None, str], None] | None = None,
    ) -> list[Document]:
        """Run a Firecrawl crawl using WebSocket-based watcher for real-time progress.

        This method uses Firecrawl's AsyncWatcher which connects via WebSocket
        for real-time job progress updates, falling back to HTTP polling if
        WebSocket connection fails.
        """
        request_kwargs = self._prepare_async_crawl_params(params)

        self.logger.info(
            "Starting async Firecrawl crawl job with watcher",
            extra={
                "url": url,
                "params": request_kwargs,
            },
        )

        # Start the crawl job
        start_response = await self.async_firecrawl_client.start_crawl(url=url, **request_kwargs)
        job_id = getattr(start_response, "id", None) or start_response.get("id")  # type: ignore[union-attr]
        if not job_id:
            raise RuntimeError("Failed to start Firecrawl crawl job (missing job ID)")

        timeout_seconds = math.ceil(self.timeout_ms / 1000) if self.timeout_ms else None
        poll_interval = max(params.get("delay", 0) / 1000 if params.get("delay") else 2, 1)

        self.logger.info(
            "Watching crawl job via WebSocket",
            extra={
                "job_id": job_id,
                "timeout": timeout_seconds,
                "poll_interval": poll_interval,
            },
        )

        collected_docs: list[Any] = []
        final_status: str = "unknown"

        # Use AsyncWatcher for real-time progress
        # NOTE: AsyncWatcher may fail due to Firecrawl SDK bug where CrawlJob pydantic model
        # doesn't accept "discovering" status. We catch this and fall back to HTTP polling.
        try:
            async for snapshot in AsyncWatcher(
                self.async_firecrawl_client,
                job_id,
                kind="crawl",
                poll_interval=int(poll_interval),
                timeout=timeout_seconds,
            ):
                final_status = snapshot.status
                completed_count = getattr(snapshot, "completed", 0)
                total_count = getattr(snapshot, "total", None)

                # Extract documents from snapshot (Firecrawl returns all docs in data field)
                if hasattr(snapshot, "data") and snapshot.data:
                    collected_docs = snapshot.data
                    print(f"[WATCHER DEBUG] Got {len(snapshot.data)} docs from snapshot, status={final_status}")

                self.logger.debug(
                    "Firecrawl crawl progress via watcher",
                    extra={
                        "job_id": job_id,
                        "status": final_status,
                        "completed": completed_count,
                        "total": total_count,
                        "docs": len(collected_docs) if collected_docs else 0,
                    },
                )

                # Call progress callback if provided
                if progress_callback:
                    progress_callback(completed_count, total_count, final_status)

                # Terminal status check
                if final_status in ("completed", "failed", "cancelled"):
                    break

            if final_status == "failed":
                raise RuntimeError(f"Firecrawl crawl job {job_id} failed")

            if final_status == "cancelled":
                raise RuntimeError(f"Firecrawl crawl job {job_id} was cancelled")

        except Exception as watcher_error:
            # Firecrawl SDK has a bug where CrawlJob doesn't accept "discovering" status
            # Fall back to HTTP polling if watcher fails
            print(f"[WATCHER DEBUG] Watcher failed: {watcher_error}, falling back to polling")
            self.logger.warning(
                "AsyncWatcher failed, falling back to HTTP polling",
                extra={
                    "job_id": job_id,
                    "error": str(watcher_error),
                    "error_type": type(watcher_error).__name__,
                },
            )
            return await self._async_crawl_with_polling(
                url=url,
                params=params,
                progress_callback=progress_callback,
            )

        print(f"[WATCHER DEBUG] Watcher completed with {len(collected_docs)} docs")
        print(f"[WATCHER DEBUG] Doc types: {[type(d).__name__ for d in collected_docs[:3]] if collected_docs else 'NONE'}")

        self.logger.info(
            "Async Firecrawl crawl completed via watcher",
            extra={
                "job_id": job_id,
                "document_count": len(collected_docs),
                "doc_types": [type(d).__name__ for d in collected_docs[:3]] if collected_docs else [],
                "first_doc_sample": str(collected_docs[0])[:200] if collected_docs else "NO DOCS",
            },
        )

        # Convert Firecrawl Document objects to our Document model
        return self._convert_to_documents(collected_docs, source_url=url)

    def _prepare_async_crawl_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """Filter and adapt crawl parameters for the async Firecrawl client."""
        allowed_keys = {
            "limit",
            "max_discovery_depth",
            "include_paths",
            "exclude_paths",
            "max_concurrency",
            "delay",
            "integration",
            "prompt",
            "crawl_entire_domain",
            "allow_external_links",
            "allow_subdomains",
            "sitemap",
            "ignore_sitemap",
            "ignore_query_parameters",
            "zero_data_retention",
            "scrape_options",
        }

        request: dict[str, Any] = {}
        for key, value in params.items():
            if key in allowed_keys and value is not None:
                request[key] = value

        scrape_options = request.get("scrape_options")
        if isinstance(scrape_options, dict) and scrape_options:
            request["scrape_options"] = scrape_options

        return request

    def _run_sync_crawl_with_watcher(self, *, url: str, params: dict[str, Any]) -> list[Document]:
        """Synchronously run the async crawl helper for CLI compatibility."""

        async def _runner() -> list[Document]:
            return await self._async_crawl_with_watcher(url=url, params=params)

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(_runner())

        new_loop = asyncio.new_event_loop()
        try:
            return new_loop.run_until_complete(_runner())
        finally:
            new_loop.close()

    def _glob_to_regex(self, pattern: str) -> str:
        """Convert glob pattern to regex pattern for Firecrawl API.

        Args:
            pattern: Glob pattern (e.g., '**/fr/**', '*/docs/*') or raw regex (starts with ^)

        Returns:
            Regex pattern compatible with Firecrawl API (ReDoS-safe)
        """
        # If already a regex (starts with ^), return as-is without modification
        if pattern.startswith("^"):
            return pattern

        # Simplify glob patterns to avoid ReDoS
        # **/foo/** -> /foo/ (just match the segment anywhere in path)
        # */foo/* -> /foo/ (same - Firecrawl will handle the rest)
        import re

        # Extract the core path component (strip leading/trailing wildcards)
        pattern_stripped = pattern.strip("*").strip("/")

        # If pattern is just wildcards, return a safe catch-all
        if not pattern_stripped:
            return ".*"

        # Build a simple, safe regex that matches the path component
        # Example: **/es/** -> es/.* (matches any path containing es/)
        # Format matches Firecrawl docs: "blog/.*" pattern style
        regex = re.escape(pattern_stripped)
        regex = f"{regex}/.*"

        return regex

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
            params["limit"] = limit
            params["max_discovery_depth"] = max_depth  # Firecrawl Python SDK uses snake_case

            # Add include_paths/exclude_paths for URL-based filtering (Layer 1)
            # Firecrawl Python SDK expects regex patterns in snake_case
            # NOTE: Only convert glob patterns - skip raw regex (^...)
            # as they may trigger Firecrawl's ReDoS detector
            if self.include_paths and len(self.include_paths) > 0:
                converted_includes = [
                    self._glob_to_regex(p) for p in self.include_paths
                    if not p.startswith("^")  # Skip raw regex patterns
                ]
                if converted_includes:
                    params["include_paths"] = converted_includes
                    self.logger.info(
                        f"Crawl including {len(converted_includes)} URL patterns",
                        extra={
                            "sample_patterns": converted_includes[:5],
                            "total_count": len(converted_includes)
                        }
                    )
            if self.exclude_paths and len(self.exclude_paths) > 0:
                converted_excludes = [
                    self._glob_to_regex(p) for p in self.exclude_paths
                    if not p.startswith("^")  # Skip raw regex patterns
                ]
                if converted_excludes:
                    params["exclude_paths"] = converted_excludes
                    self.logger.info(
                        f"Crawl excluding {len(converted_excludes)} URL patterns",
                        extra={
                            "sample_patterns": converted_excludes[:5],
                            "total_count": len(converted_excludes)
                        }
                    )
            if self.max_concurrency is not None:
                params["max_concurrency"] = self.max_concurrency  # snake_case for SDK
            if self.crawl_delay_ms is not None:
                params["delay"] = max(math.ceil(self.crawl_delay_ms / 1000), 0)

            scrape_options: dict[str, Any] = {}
            if formats:
                scrape_options["formats"] = formats
            self._apply_cache_options(scrape_options)
            self._apply_location(scrape_options, mode="crawl")
            if scrape_options:
                params["scrape_options"] = scrape_options

        elif mode == "scrape":
            if formats:
                params["formats"] = formats
            if self.cache_max_age_ms:
                params["max_age"] = self.cache_max_age_ms
                params["store_in_cache"] = True
            self._apply_location(params, mode="scrape")

        elif mode == "map":
            # Map mode uses limit for URL discovery (no content fetching, so no formats)
            params["limit"] = limit
            if self.location:
                params["location"] = self._build_location()

        elif mode == "extract":
            # Extract mode might have schema or prompt
            if "schema" in kwargs:
                params["schema"] = kwargs["schema"]
            if "prompt" in kwargs:
                params["prompt"] = kwargs["prompt"]
            scrape_options: dict[str, Any] = {}
            if formats:
                scrape_options["formats"] = formats
            self._apply_cache_options(scrape_options)
            self._apply_location(scrape_options, mode="extract")
            if scrape_options:
                params["scrape_options"] = scrape_options

        # Merge any additional kwargs
        for key, value in kwargs.items():
            if key not in ("schema", "prompt"):  # Already handled above
                params[key] = value

        return params

    def _apply_cache_options(self, target: dict[str, Any]) -> None:
        """Attach cache controls to scrape options if enabled."""
        if self.cache_max_age_ms and self.cache_max_age_ms > 0:
            target["max_age"] = self.cache_max_age_ms
            target["store_in_cache"] = True

    def _apply_location(self, target: dict[str, Any], *, mode: str) -> None:
        """Attach location configuration to the appropriate parameter structure."""
        if not self.location:
            return
        location_payload = self._build_location()
        if mode == "scrape":
            target["location"] = location_payload
        else:
            # For crawl/extract the location must be embedded in scrape_options
            target["location"] = location_payload

    def _build_location(self) -> dict[str, Any]:
        """Construct Firecrawl location payload."""
        country = self.location.get("country", "US") if self.location else "US"
        languages = self.location.get("languages", ["en-US"]) if self.location else ["en-US"]
        return {"country": country, "languages": languages}

    def _metadata_to_dict(self, metadata: Any) -> dict[str, Any]:
        """Convert Firecrawl metadata structures into plain dictionaries."""
        if metadata is None:
            return {}
        if isinstance(metadata, dict):
            return {k: v for k, v in metadata.items() if v not in (None, "", [], {})}
        if hasattr(metadata, "model_dump") and callable(metadata.model_dump):
            try:
                return {
                    k: v
                    for k, v in metadata.model_dump(exclude_none=True).items()
                    if v not in (None, "", [], {})
                }
            except Exception:
                pass
        if hasattr(metadata, "dict") and callable(metadata.dict):
            try:
                return {
                    k: v
                    for k, v in metadata.dict(exclude_none=True).items()  # type: ignore[attr-defined]
                    if v not in (None, "", [], {})
                }
            except Exception:
                pass
        return {}

    def _extract_content(self, raw_doc: Any) -> str:
        """Extract best-effort textual content from Firecrawl documents."""
        candidates: list[str] = []

        def _add_candidate(value: Any) -> None:
            if isinstance(value, str) and value.strip():
                candidates.append(value)

        if isinstance(raw_doc, dict):
            for key in ("content", "markdown", "text", "html", "raw_html", "rawHtml", "summary"):
                _add_candidate(raw_doc.get(key))
        else:
            for attr in ("text", "markdown", "content", "html", "raw_html", "rawHtml", "summary"):
                value = getattr(raw_doc, attr, None)
                if callable(value):
                    try:
                        value = value()
                    except Exception:
                        value = None
                _add_candidate(value)

        if candidates:
            return candidates[0]

        # Fallback: convert entire object to string if nothing else
        if isinstance(raw_doc, dict):
            return str(raw_doc)

        return str(getattr(raw_doc, "__dict__", raw_doc))

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
        filtered_by_language = 0
        timestamp = datetime.now(UTC)

        for idx, raw_doc in enumerate(llamaindex_docs):
            content = self._extract_content(raw_doc)

            if isinstance(raw_doc, dict):
                metadata_source = raw_doc.get("metadata", {})
            else:
                metadata_source = getattr(raw_doc, "metadata", {})

            llama_metadata = self._metadata_to_dict(metadata_source)

            # Include top-level fields that may carry useful metadata
            if isinstance(raw_doc, dict):
                for key in ("url", "title", "description", "language"):
                    value = raw_doc.get(key)
                    if value and key not in llama_metadata:
                        llama_metadata[key] = value
            else:
                for attr in ("url", "title", "description", "language"):
                    value = getattr(raw_doc, attr, None)
                    if value and attr not in llama_metadata:
                        llama_metadata[attr] = value

            sanitized_metadata = self._sanitize_firecrawl_metadata(llama_metadata)

            # Filter by metadata language if enabled
            if self.filter_non_english_metadata:
                detected_lang = sanitized_metadata.get("language", "").lower()
                if detected_lang and detected_lang not in ["en", "en-us", "en-gb"]:
                    filtered_by_language += 1
                    doc_url = (
                        sanitized_metadata.get("url")
                        or sanitized_metadata.get("source_url")
                        or llama_metadata.get("url")
                        or source_url
                    )
                    self.logger.debug(
                        f"Filtered document by metadata language: {detected_lang}",
                        extra={
                            "source": self.source_name,
                            "source_url": doc_url,
                            "language": detected_lang,
                        },
                    )
                    continue

            # Generate unique document ID
            # Use URL from metadata if available, otherwise use source_url
            doc_url = (
                sanitized_metadata.get("url")
                or sanitized_metadata.get("source_url")
                or llama_metadata.get("url")
                or getattr(raw_doc, "url", None)
                or source_url
            )
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

        # Log filtering statistics
        if filtered_by_language > 0:
            self.logger.info(
                f"Filtered {filtered_by_language} non-English documents by metadata",
                extra={
                    "source": self.source_name,
                    "filtered_count": filtered_by_language,
                    "kept_count": len(documents),
                },
            )

        return documents

    def _sanitize_firecrawl_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """Reduce Firecrawl metadata to a compact subset to avoid oversized chunks."""
        sanitized: dict[str, Any] = {}
        if not isinstance(metadata, dict):
            return sanitized

        for key in self.ALLOWED_METADATA_KEYS:
            if key in metadata and metadata[key] not in (None, "", [], {}):
                sanitized[key] = self._truncate_metadata_value(metadata[key])

        # Include additional metadata keys while ensuring payload limits
        for key, value in metadata.items():
            if key in sanitized:
                continue
            if value in (None, "", [], {}):
                continue
            sanitized[key] = self._truncate_metadata_value(value)

        return sanitized

    def _truncate_metadata_value(self, value: Any, depth: int = 0) -> Any:
        """Truncate metadata values to keep payload sizes manageable."""
        if isinstance(value, str):
            if len(value) > self.max_metadata_chars:
                return value[: self.max_metadata_chars] + "..."
            return value
        if isinstance(value, int | float | bool) or value is None:
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
