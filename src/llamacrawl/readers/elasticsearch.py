"""Elasticsearch reader for ingesting documents from Elasticsearch indices.

This module provides the ElasticsearchReader class for loading documents from
Elasticsearch indices with support for:
1. Modern search_after with Point-in-Time (PIT) pagination (ES 7.10+)
2. Fallback to scroll API for older Elasticsearch versions (< 7.10)
3. Incremental sync using timestamp fields
4. Configurable field mappings
5. Index pattern support (e.g., "docs-*")

The reader uses elasticsearch-py client directly for full control over pagination
and modern search features.
"""

import hashlib
import os
from datetime import datetime
from typing import Any

from elasticsearch import Elasticsearch

from llamacrawl.models.document import Document, DocumentMetadata
from llamacrawl.readers.base import BaseReader
from llamacrawl.storage.redis import RedisClient


class ElasticsearchReader(BaseReader):
    """Reader for Elasticsearch indices.

    This reader loads documents from Elasticsearch with support for:
    - Point-in-Time (PIT) with search_after pagination (ES 7.10+)
    - Scroll API fallback for older ES versions (< 7.10)
    - Incremental sync using timestamp fields
    - Configurable field mappings
    - Index pattern support

    Attributes:
        source_name: Name of the data source (elasticsearch)
        config: Source-specific configuration from config.yaml
        redis_client: Redis client for state management
        es_client: Elasticsearch client instance
        field_mappings: Field name mappings for document conversion
        batch_size: Number of documents per page (default 200-1000)
        timestamp_field: Field name for timestamp-based filtering
    """

    def __init__(
        self,
        source_name: str,
        config: dict[str, Any],
        redis_client: RedisClient,
    ):
        """Initialize ElasticsearchReader.

        Args:
            source_name: Name of the data source (elasticsearch)
            config: Source-specific configuration from config.yaml
            redis_client: Redis client for state management

        Raises:
            ValueError: If required credentials are missing or invalid
        """
        super().__init__(source_name, config, redis_client)

        # Validate credentials
        self.validate_credentials(["ELASTICSEARCH_URL"])

        # Initialize Elasticsearch client
        es_url = os.environ["ELASTICSEARCH_URL"]
        es_api_key = os.environ.get("ELASTICSEARCH_API_KEY")

        client_kwargs: dict[str, Any] = {}
        if es_api_key:
            client_kwargs["api_key"] = es_api_key
        else:
            self.logger.warning(
                "ELASTICSEARCH_API_KEY not set - connecting without authentication",
                extra={"source": self.source_name}
            )

        try:
            self.es_client = Elasticsearch(es_url, **client_kwargs)
            # Test connection
            info = self.es_client.info()
            self.es_version = info["version"]["number"]
            self.logger.info(
                f"Connected to Elasticsearch {self.es_version}",
                extra={"source": self.source_name, "es_version": self.es_version}
            )
        except Exception as e:
            self.logger.error(
                f"Failed to connect to Elasticsearch at {es_url}: {e}",
                extra={"source": self.source_name, "error": str(e)}
            )
            raise ValueError(f"Failed to connect to Elasticsearch: {e}") from e

        # Get field mappings from config
        self.field_mappings = config.get("field_mappings", {
            "title": "title",
            "content": "content",
            "timestamp": "@timestamp"
        })

        # Get batch size from config
        self.batch_size = config.get("batch_size", 500)

        # Get timestamp field for incremental sync
        self.timestamp_field = self.field_mappings.get("timestamp", "@timestamp")

        self.logger.info(
            "ElasticsearchReader initialized",
            extra={
                "source": self.source_name,
                "field_mappings": self.field_mappings,
                "batch_size": self.batch_size,
                "timestamp_field": self.timestamp_field
            }
        )

    def load_data(self, **kwargs: Any) -> list[Document]:
        """Load documents from Elasticsearch indices.

        Supports incremental sync using timestamp-based filtering. Uses modern
        search_after with Point-in-Time (PIT) for ES 7.10+, falls back to scroll
        API for older versions.

        Args:
            **kwargs: Optional parameters:
                - indices: Override indices from config (list[str] or str)
                - query_filter: Override query filter from config (dict)

        Returns:
            List of Document objects loaded from Elasticsearch

        Raises:
            ValueError: If indices not specified in config or kwargs
            Exception: Various Elasticsearch errors (connection, query, etc.)
        """
        # Get indices from kwargs or config
        indices = kwargs.get("indices", self.config.get("indices", []))
        if not indices:
            raise ValueError("No indices specified in config or kwargs")

        # Convert to list if string
        if isinstance(indices, str):
            indices = [indices]

        # Get query filter
        query_filter = kwargs.get("query_filter", self.config.get("query_filter", {}))

        # Build query with incremental sync support
        query = self._build_query(query_filter)

        self.logger.info(
            f"Loading documents from Elasticsearch indices: {indices}",
            extra={
                "source": self.source_name,
                "indices": indices,
                "query": query
            }
        )

        # Choose pagination strategy based on ES version
        if self._supports_pit():
            documents = self._load_with_pit(indices, query)
        else:
            documents = self._load_with_scroll(indices, query)

        # Update cursor if incremental sync is supported
        if documents and self.supports_incremental_sync():
            latest_timestamp = max(
                doc.metadata.timestamp for doc in documents
            )
            self.set_last_cursor(latest_timestamp.isoformat())

        self.log_load_summary(
            total_fetched=len(documents),
            indices=indices,
            incremental_sync=self.supports_incremental_sync()
        )

        return documents

    def supports_incremental_sync(self) -> bool:
        """Check if incremental sync is supported.

        Returns:
            True if the configured indices have timestamp fields, False otherwise
        """
        # Incremental sync requires timestamp field
        # We check if timestamp field is configured (assumes it exists if configured)
        return self.timestamp_field is not None

    def _build_query(self, query_filter: dict[str, Any]) -> dict[str, Any]:
        """Build Elasticsearch query with incremental sync support.

        Args:
            query_filter: Base query filter from config

        Returns:
            Complete Elasticsearch query with range filter if cursor exists
        """
        # Start with base query filter or match_all
        query = query_filter.copy() if query_filter else {"match_all": {}}

        # Add incremental sync filter if supported and cursor exists
        last_cursor = self.get_last_cursor()
        if last_cursor and self.supports_incremental_sync():
            self.logger.info(
                f"Using incremental sync with cursor: {last_cursor}",
                extra={"source": self.source_name, "cursor": last_cursor}
            )

            # Wrap in bool query with range filter
            if "bool" not in query:
                query = {
                    "bool": {
                        "must": [{"match_all": {}}] if query == {"match_all": {}} else [query]
                    }
                }

            # Add range filter for timestamp > cursor
            if "must" not in query["bool"]:
                query["bool"]["must"] = []

            query["bool"]["must"].append({
                "range": {
                    self.timestamp_field: {
                        "gt": last_cursor
                    }
                }
            })

        return {"query": query}

    def _supports_pit(self) -> bool:
        """Check if Elasticsearch version supports Point-in-Time API.

        Returns:
            True if ES version >= 7.10, False otherwise
        """
        try:
            major, minor, *_ = map(int, self.es_version.split("."))
            return major > 7 or (major == 7 and minor >= 10)
        except (ValueError, AttributeError):
            self.logger.warning(
                f"Could not parse ES version {self.es_version}, falling back to scroll API",
                extra={"source": self.source_name}
            )
            return False

    def _load_with_pit(self, indices: list[str], query: dict[str, Any]) -> list[Document]:
        """Load documents using Point-in-Time with search_after pagination.

        Modern pagination method for ES 7.10+. More efficient than scroll API.

        Args:
            indices: List of index patterns to search
            query: Elasticsearch query DSL

        Returns:
            List of Document objects
        """
        self.logger.info(
            "Using Point-in-Time (PIT) with search_after for pagination",
            extra={"source": self.source_name}
        )

        documents: list[Document] = []

        try:
            # Open Point-in-Time
            pit_response = self.es_client.open_point_in_time(
                index=",".join(indices),
                keep_alive="5m"
            )
            pit_id = pit_response["id"]

            self.logger.debug(
                f"Opened PIT: {pit_id}",
                extra={"source": self.source_name, "pit_id": pit_id}
            )

            # Search parameters with PIT
            search_params = {
                **query,
                "size": self.batch_size,
                "pit": {
                    "id": pit_id,
                    "keep_alive": "5m"
                },
                "sort": [
                    {self.timestamp_field: {"order": "asc"}},
                    {"_id": {"order": "asc"}}  # Tie-breaker
                ],
                "track_total_hits": False  # Performance optimization
            }

            search_after = None

            # Paginate using search_after
            while True:
                if search_after:
                    search_params["search_after"] = search_after

                response = self.es_client.search(**search_params)
                hits = response["hits"]["hits"]

                if not hits:
                    break

                # Convert hits to documents
                for hit in hits:
                    try:
                        doc = self._hit_to_document(hit)
                        documents.append(doc)
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to convert hit to document: {e}",
                            extra={
                                "source": self.source_name,
                                "hit_id": hit.get("_id"),
                                "error": str(e)
                            }
                        )

                # Get sort values from last hit for next page
                search_after = hits[-1]["sort"]

                self.logger.debug(
                    f"Loaded {len(hits)} documents from current page",
                    extra={
                        "source": self.source_name,
                        "total_so_far": len(documents)
                    }
                )

        finally:
            # Always close PIT to free resources
            try:
                if pit_id:
                    self.es_client.close_point_in_time(id=pit_id)
                    self.logger.debug(
                        f"Closed PIT: {pit_id}",
                        extra={"source": self.source_name}
                    )
            except Exception as e:
                self.logger.warning(
                    f"Failed to close PIT: {e}",
                    extra={"source": self.source_name, "error": str(e)}
                )

        return documents

    def _load_with_scroll(self, indices: list[str], query: dict[str, Any]) -> list[Document]:
        """Load documents using scroll API (fallback for ES < 7.10).

        Legacy pagination method. Still functional but deprecated.

        Args:
            indices: List of index patterns to search
            query: Elasticsearch query DSL

        Returns:
            List of Document objects
        """
        self.logger.warning(
            "Using deprecated scroll API (ES version < 7.10)",
            extra={"source": self.source_name, "es_version": self.es_version}
        )

        documents: list[Document] = []

        # Initial search with scroll
        response = self.es_client.search(
            index=",".join(indices),
            scroll="5m",
            size=self.batch_size,
            **query,
            sort=[
                {self.timestamp_field: {"order": "asc"}},
                {"_id": {"order": "asc"}}
            ]
        )

        scroll_id = response["_scroll_id"]

        try:
            # Process initial batch
            hits = response["hits"]["hits"]
            while hits:
                # Convert hits to documents
                for hit in hits:
                    try:
                        doc = self._hit_to_document(hit)
                        documents.append(doc)
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to convert hit to document: {e}",
                            extra={
                                "source": self.source_name,
                                "hit_id": hit.get("_id"),
                                "error": str(e)
                            }
                        )

                self.logger.debug(
                    f"Loaded {len(hits)} documents from scroll page",
                    extra={
                        "source": self.source_name,
                        "total_so_far": len(documents)
                    }
                )

                # Get next batch
                response = self.es_client.scroll(
                    scroll_id=scroll_id,
                    scroll="5m"
                )
                hits = response["hits"]["hits"]
                scroll_id = response["_scroll_id"]

        finally:
            # Clear scroll context
            try:
                self.es_client.clear_scroll(scroll_id=scroll_id)
            except Exception as e:
                self.logger.warning(
                    f"Failed to clear scroll: {e}",
                    extra={"source": self.source_name, "error": str(e)}
                )

        return documents

    def _hit_to_document(self, hit: dict[str, Any]) -> Document:
        """Convert Elasticsearch hit to Document object.

        Args:
            hit: Elasticsearch search hit

        Returns:
            Document object

        Raises:
            ValueError: If required fields are missing
        """
        source = hit["_source"]
        index = hit["_index"]
        doc_id_raw = hit["_id"]

        # Extract fields using configured mappings
        title_field = self.field_mappings.get("title", "title")
        content_field = self.field_mappings.get("content", "content")

        title = source.get(title_field, f"Document from {index}")
        content = source.get(content_field)

        if not content:
            raise ValueError(f"Content field '{content_field}' is missing or empty")

        # Get timestamp
        timestamp_raw = source.get(self.timestamp_field)
        if timestamp_raw:
            if isinstance(timestamp_raw, str):
                timestamp = datetime.fromisoformat(timestamp_raw.replace("Z", "+00:00"))
            else:
                # Assume epoch timestamp
                timestamp = datetime.fromtimestamp(timestamp_raw / 1000.0)
        else:
            # Default to now if no timestamp
            timestamp = datetime.now()

        # Create document ID
        doc_id = f"elasticsearch_{index}_{doc_id_raw}"

        # Calculate content hash
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Build metadata
        metadata = DocumentMetadata(
            source_type="elasticsearch",
            source_url=f"{os.environ['ELASTICSEARCH_URL']}/{index}/_doc/{doc_id_raw}",
            timestamp=timestamp,
            extra={
                "index": index,
                "es_id": doc_id_raw,
                "es_score": hit.get("_score"),
            }
        )

        return Document(
            doc_id=doc_id,
            title=title,
            content=content,
            content_hash=content_hash,
            metadata=metadata
        )

    def get_api_client(self) -> Elasticsearch:
        """Get Elasticsearch client instance.

        Returns:
            Elasticsearch client
        """
        return self.es_client
