"""Async Firecrawl web scraping reader for LlamaCrawl.

This module provides AsyncFirecrawlReader that uses Firecrawl's native async client
for better performance and concurrency when crawling/scraping multiple pages.
"""

import hashlib
import os
from datetime import UTC, datetime
from typing import Any, Literal
from urllib.parse import urlparse

from firecrawl.v2.client_async import AsyncFirecrawlClient
from llama_index.core.readers.base import BasePydanticReader
from llama_index.core.schema import Document as LlamaDocument

from llamacrawl.models.document import Document, DocumentMetadata
from llamacrawl.readers.base import BaseReader
from llamacrawl.storage.redis import RedisClient
from llamacrawl.utils.retry import retry_with_backoff


class AsyncFirecrawlReader(BaseReader):
    """Async Firecrawl web scraping reader using native async client.

    This reader uses Firecrawl's v2 async API directly for better performance
    compared to the synchronous LlamaIndex FireCrawlWebReader.

    Attributes:
        source_name: Name of the data source
        config: Firecrawl-specific configuration
        redis_client: Redis client for state management
        api_url: Firecrawl API URL from environment
        api_key: Firecrawl API key from environment
        async_client: Firecrawl AsyncFirecrawlClient instance
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
        """Initialize Async Firecrawl reader.

        Args:
            source_name: Name of the data source
            config: Firecrawl-specific configuration
            redis_client: Redis client instance

        Raises:
            ValueError: If required environment variables are missing
        """
        super().__init__(source_name, config, redis_client)

        # Validate required environment variables
        self.validate_credentials(["FIRECRAWL_API_URL", "FIRECRAWL_API_KEY"])

        self.api_url = os.environ["FIRECRAWL_API_URL"]
        self.api_key = os.environ["FIRECRAWL_API_KEY"]

        if self.api_key.startswith("fc-xxx"):
            raise ValueError(
                "Invalid FIRECRAWL_API_KEY. Please set a valid API key in .env file."
            )

        self.include_paths: list[str] = config.get("include_paths", []) or []
        self.exclude_paths: list[str] = config.get("exclude_paths", []) or []
        self.filter_non_english_metadata = config.get("filter_non_english_metadata", True)

        # Initialize async client
        self.async_client = AsyncFirecrawlClient(
            api_key=self.api_key,
            api_url=self.api_url,
        )

    async def aload_data(
        self,
        url: str | list[str] | None = None,
        mode: Literal["scrape", "crawl", "map", "extract"] = "scrape",
        limit: int | None = None,
        max_depth: int | None = None,
        formats: list[str] | None = None,
        **kwargs: Any,
    ) -> list[Document]:
        """Asynchronously load documents from Firecrawl.

        This method fetches web content via Firecrawl's async API and converts
        it to Document objects with proper metadata.

        Args:
            url: URL(s) to scrape/crawl
            mode: Firecrawl mode (scrape/crawl/map/extract)
            limit: Maximum number of pages to fetch
            max_depth: Maximum crawl depth for crawl mode
            formats: Output formats (markdown, html)
            **kwargs: Additional Firecrawl API parameters

        Returns:
            List of Document objects with web content

        Raises:
            ValueError: If URL is invalid or mode is unsupported
            Exception: Various Firecrawl API errors
        """
        # Determine URLs to process
        urls_to_process: list[str] = []

        if url is None:
            config_urls = self.config.get("urls", [])
            if not config_urls:
                raise ValueError("No URLs provided")
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
            f"Async loading data from {len(urls_to_process)} URL(s) in {mode} mode",
            extra={
                "source": self.source_name,
                "mode": mode,
                "url_count": len(urls_to_process),
                "limit": limit,
                "max_depth": max_depth if mode == "crawl" else None,
            },
        )

        # Process all URLs concurrently
        import asyncio
        tasks = [
            self._aload_single_url(
                url=url_str,
                mode=mode,
                limit=limit,
                max_depth=max_depth,
                formats=formats,
                **kwargs,
            )
            for url_str in urls_to_process
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_documents: list[Document] = []
        for url_str, result in zip(urls_to_process, results):
            if isinstance(result, Exception):
                self.logger.error(
                    f"Failed to load URL {url_str}: {result}",
                    extra={
                        "source": self.source_name,
                        "url": url_str,
                        "error": str(result),
                        "error_type": type(result).__name__,
                    },
                )
            else:
                all_documents.extend(result)
                self.logger.info(
                    f"Loaded {len(result)} documents from {url_str}",
                    extra={
                        "source": self.source_name,
                        "url": url_str,
                        "document_count": len(result),
                    },
                )

        # Log summary
        self.log_load_summary(
            total_fetched=len(all_documents),
            filtered_count=0,
            error_count=sum(1 for r in results if isinstance(r, Exception)),
            mode=mode,
            url_count=len(urls_to_process),
        )

        return all_documents

    async def _aload_single_url(
        self,
        url: str,
        mode: Literal["scrape", "crawl", "map", "extract"],
        limit: int,
        max_depth: int,
        formats: list[str],
        **kwargs: Any,
    ) -> list[Document]:
        """Load documents from a single URL using async Firecrawl API.

        Args:
            url: URL to scrape/crawl
            mode: Firecrawl mode
            limit: Maximum pages
            max_depth: Maximum crawl depth
            formats: Output formats
            **kwargs: Additional parameters

        Returns:
            List of Document objects
        """
        documents: list[Document] = []
        
        try:
            if mode == "scrape":
                # Single page scraping
                response = await self.async_client.scrape(
                    url=url,
                    formats=formats,
                    includePaths=self.include_paths if self.include_paths else None,
                    excludePaths=self.exclude_paths if self.exclude_paths else None,
                    **kwargs,
                )
                documents.append(self._convert_to_document(response, url, mode))
                
            elif mode == "crawl":
                # Full site crawling
                response = await self.async_client.crawl(
                    url=url,
                    maxDepth=max_depth,
                    limit=limit,
                    formats=formats,
                    includePaths=self.include_paths if self.include_paths else None,
                    excludePaths=self.exclude_paths if self.exclude_paths else None,
                    **kwargs,
                )
                
                # Process crawl results
                if hasattr(response, 'data') and response.data:
                    for page_data in response.data:
                        documents.append(self._convert_to_document(page_data, url, mode))
                        
            elif mode == "map":
                # URL discovery
                response = await self.async_client.map(
                    url=url,
                    limit=limit,
                    **kwargs,
                )
                
                # Convert links to documents
                if hasattr(response, 'links') and response.links:
                    for link in response.links:
                        doc = Document(
                            doc_id=self._generate_doc_id(link.url if hasattr(link, 'url') else str(link)),
                            title=getattr(link, 'title', ''),
                            content=getattr(link, 'description', link.url if hasattr(link, 'url') else str(link)),
                            content_hash=self._hash_content(str(link)),
                            metadata=DocumentMetadata(
                                source_type="firecrawl",
                                source_url=link.url if hasattr(link, 'url') else str(link),
                                timestamp=datetime.now(UTC),
                                extra={
                                    "mode": mode,
                                    "title": getattr(link, 'title', ''),
                                    "description": getattr(link, 'description', ''),
                                },
                            ),
                        )
                        documents.append(doc)
                        
            elif mode == "extract":
                # Structured extraction
                prompt = kwargs.pop("prompt", None)
                schema = kwargs.pop("schema", None)
                
                if not prompt and not schema:
                    raise ValueError("Extract mode requires either 'prompt' or 'schema'")
                
                response = await self.async_client.extract(
                    urls=[url],
                    prompt=prompt,
                    schema=schema,
                    **kwargs,
                )
                
                # Convert extraction results
                if hasattr(response, 'data') and response.data:
                    for extraction in response.data:
                        doc = Document(
                            doc_id=self._generate_doc_id(url),
                            title=f"Extraction from {url}",
                            content=str(extraction),
                            content_hash=self._hash_content(str(extraction)),
                            metadata=DocumentMetadata(
                                source_type="firecrawl",
                                source_url=url,
                                timestamp=datetime.now(UTC),
                                extra={
                                    "mode": mode,
                                    "extracted_data": extraction,
                                },
                            ),
                        )
                        documents.append(doc)
            else:
                raise ValueError(f"Unsupported mode: {mode}")
                
        except Exception as e:
            self.logger.error(
                f"Error in async Firecrawl {mode} for {url}: {e}",
                extra={
                    "source": self.source_name,
                    "url": url,
                    "mode": mode,
                    "error": str(e),
                },
            )
            raise

        # Filter non-English content if configured
        if self.filter_non_english_metadata:
            documents = [
                doc for doc in documents
                if self._is_english(doc.metadata.extra.get("language", "en"))
            ]

        return documents

    def _convert_to_document(self, firecrawl_data: Any, url: str, mode: str) -> Document:
        """Convert Firecrawl response data to Document object.

        Args:
            firecrawl_data: Response from Firecrawl API
            url: Original URL
            mode: Operation mode

        Returns:
            Document object
        """
        # Extract content
        content = ""
        if hasattr(firecrawl_data, 'markdown') and firecrawl_data.markdown:
            content = firecrawl_data.markdown
        elif hasattr(firecrawl_data, 'html') and firecrawl_data.html:
            content = firecrawl_data.html
        elif hasattr(firecrawl_data, 'text') and firecrawl_data.text:
            content = firecrawl_data.text
        elif isinstance(firecrawl_data, dict):
            content = firecrawl_data.get('markdown', '') or firecrawl_data.get('html', '') or firecrawl_data.get('text', '')

        # Extract metadata
        metadata_dict: dict[str, Any] = {"mode": mode}
        
        if hasattr(firecrawl_data, 'metadata'):
            raw_metadata = firecrawl_data.metadata
            if isinstance(raw_metadata, dict):
                metadata_dict.update(raw_metadata)
            else:
                # Try to extract from object attributes
                for key in self.ALLOWED_METADATA_KEYS:
                    value = getattr(raw_metadata, key, None)
                    if value is not None:
                        metadata_dict[key] = value
        
        # Get source URL
        source_url = url
        if hasattr(firecrawl_data, 'url') and firecrawl_data.url:
            source_url = firecrawl_data.url
        elif isinstance(firecrawl_data, dict) and 'url' in firecrawl_data:
            source_url = firecrawl_data['url']

        # Generate document
        doc_id = self._generate_doc_id(source_url)
        title = metadata_dict.get("title", "") or metadata_dict.get("ogTitle", "")

        return Document(
            doc_id=doc_id,
            title=title,
            content=content,
            content_hash=self._hash_content(content),
            metadata=DocumentMetadata(
                source_type="firecrawl",
                source_url=source_url,
                timestamp=datetime.now(UTC),
                extra=metadata_dict,
            ),
        )

    def _generate_doc_id(self, url: str) -> str:
        """Generate unique document ID from URL."""
        return f"firecrawl_{hashlib.md5(url.encode()).hexdigest()[:12]}"

    def _hash_content(self, content: str) -> str:
        """Generate SHA-256 hash of content."""
        return hashlib.sha256(content.encode()).hexdigest()

    def _validate_url(self, url: str) -> bool:
        """Validate URL format."""
        try:
            result = urlparse(url)
            return bool(result.scheme and result.netloc)
        except ValueError:
            return False

    def _is_english(self, language: str) -> bool:
        """Check if language code indicates English content."""
        if not language:
            return True  # Default to including if no language specified
        lang_lower = language.lower()
        return lang_lower in {"en", "en-us", "en-gb", "eng", "english"}

    def supports_incremental_sync(self) -> bool:
        """Check if reader supports incremental sync.
        
        Firecrawl doesn't support cursor-based incremental sync.
        """
        return False

    # Synchronous fallback using asyncio.run()
    def load_data(
        self,
        url: str | list[str] | None = None,
        mode: Literal["scrape", "crawl", "map", "extract"] = "scrape",
        limit: int | None = None,
        max_depth: int | None = None,
        formats: list[str] | None = None,
        **kwargs: Any,
    ) -> list[Document]:
        """Synchronous wrapper for async load_data.

        This allows the reader to be used in synchronous contexts.
        """
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            # Already in async context, can't use asyncio.run()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    self.aload_data(url, mode, limit, max_depth, formats, **kwargs)
                )
                return future.result()
        except RuntimeError:
            # No event loop, safe to use asyncio.run()
            return asyncio.run(
                self.aload_data(url, mode, limit, max_depth, formats, **kwargs)
            )


class AsyncFirecrawlWebReader(BasePydanticReader):
    """LlamaIndex-compatible async Firecrawl reader.

    This class provides a LlamaIndex-compatible interface while using
    Firecrawl's native async client for better performance.
    """

    api_key: str
    api_url: str | None = None
    mode: str = "scrape"
    params: dict[str, Any] | None = None

    def __init__(
        self,
        api_key: str,
        api_url: str | None = None,
        mode: str = "scrape",
        params: dict[str, Any] | None = None,
    ):
        """Initialize the async Firecrawl web reader.

        Args:
            api_key: Firecrawl API key
            api_url: Optional Firecrawl API URL
            mode: Operation mode (scrape/crawl/map/extract)
            params: Additional parameters for Firecrawl
        """
        super().__init__(
            api_key=api_key,
            api_url=api_url or "https://api.firecrawl.dev",
            mode=mode,
            params=params or {},
        )
        
        self.async_client = AsyncFirecrawlClient(
            api_key=api_key,
            api_url=api_url or "https://api.firecrawl.dev",
        )

    async def aload_data(
        self,
        url: str | None = None,
        urls: list[str] | None = None,
        query: str | None = None,
    ) -> list[LlamaDocument]:
        """Asynchronously load data from URLs.

        Args:
            url: Single URL to process
            urls: Multiple URLs to process
            query: Search query (for search mode)

        Returns:
            List of LlamaIndex Document objects
        """
        # Determine URLs to process
        urls_to_process: list[str] = []
        if url:
            urls_to_process.append(url)
        if urls:
            urls_to_process.extend(urls)
        
        if not urls_to_process and self.mode != "search":
            raise ValueError("No URLs provided")

        documents: list[LlamaDocument] = []
        
        if self.mode == "scrape":
            # Process all URLs concurrently
            import asyncio
            tasks = [
                self.async_client.scrape(url=u, **self.params)
                for u in urls_to_process
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for u, result in zip(urls_to_process, results):
                if isinstance(result, Exception):
                    continue
                
                # Convert to LlamaDocument
                text = ""
                if hasattr(result, 'markdown'):
                    text = result.markdown or ""
                elif hasattr(result, 'text'):
                    text = result.text or ""
                    
                metadata = {}
                if hasattr(result, 'metadata'):
                    if isinstance(result.metadata, dict):
                        metadata = result.metadata
                    else:
                        metadata = {
                            k: getattr(result.metadata, k, None)
                            for k in dir(result.metadata)
                            if not k.startswith('_')
                        }
                
                metadata['source_url'] = u
                documents.append(LlamaDocument(text=text, metadata=metadata))
                
        elif self.mode == "crawl":
            for u in urls_to_process:
                try:
                    result = await self.async_client.crawl(url=u, **self.params)
                    if hasattr(result, 'data') and result.data:
                        for page in result.data:
                            text = ""
                            if hasattr(page, 'markdown'):
                                text = page.markdown or ""
                            elif hasattr(page, 'text'):
                                text = page.text or ""
                                
                            metadata = {'source_url': getattr(page, 'url', u)}
                            if hasattr(page, 'metadata'):
                                if isinstance(page.metadata, dict):
                                    metadata.update(page.metadata)
                                    
                            documents.append(LlamaDocument(text=text, metadata=metadata))
                except Exception:
                    continue
                    
        elif self.mode == "search" and query:
            result = await self.async_client.search(query=query, **self.params)
            if hasattr(result, 'data') and result.data:
                for item in result.data:
                    text = getattr(item, 'markdown', '') or getattr(item, 'text', '')
                    metadata = {
                        'query': query,
                        'url': getattr(item, 'url', ''),
                        'title': getattr(item, 'title', ''),
                    }
                    documents.append(LlamaDocument(text=text, metadata=metadata))

        return documents

    def load_data(
        self,
        url: str | None = None,
        urls: list[str] | None = None,
        query: str | None = None,
    ) -> list[LlamaDocument]:
        """Synchronous wrapper for async load_data."""
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            # Already in async context
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    self.aload_data(url, urls, query)
                )
                return future.result()
        except RuntimeError:
            # No event loop
            return asyncio.run(self.aload_data(url, urls, query))