"""Elasticsearch reader using LlamaIndex.

Implements Elasticsearch document ingestion via LlamaIndex ElasticsearchReader.
Per research.md: Use LlamaIndex readers for standardized Document abstraction.
"""

import logging
from typing import Any, cast

from llama_index.core import Document
from llama_index.readers.elasticsearch import (
    ElasticsearchReader as LlamaElasticsearchReader,
)

logger = logging.getLogger(__name__)


class ElasticsearchReaderError(Exception):
    """Base exception for ElasticsearchReader errors."""

    pass


class ElasticsearchReader:
    """Elasticsearch reader using LlamaIndex ElasticsearchReader.

    Implements ingestion of documents from Elasticsearch indices.
    """

    def __init__(
        self,
        endpoint: str,
        index: str,
        max_retries: int = 3,
    ) -> None:
        """Initialize ElasticsearchReader.

        Args:
            endpoint: Elasticsearch endpoint URL (e.g., 'http://localhost:9200').
            index: Index name to query.
            max_retries: Maximum number of retry attempts (default: 3).

        Raises:
            ValueError: If endpoint or index is empty.
        """
        if not endpoint:
            raise ValueError("endpoint cannot be empty")
        if not index:
            raise ValueError("index cannot be empty")

        self.endpoint = endpoint
        self.index = index
        self.max_retries = max_retries

        logger.info(
            f"Initialized ElasticsearchReader (endpoint={endpoint}, index={index}, "
            f"max_retries={max_retries})"
        )

    def load_data(self, query: dict[str, Any], limit: int | None = None) -> list[Document]:
        """Load documents from Elasticsearch.

        Args:
            query: Elasticsearch query DSL dict (e.g., {"match_all": {}}).
            limit: Optional maximum number of documents to load.

        Returns:
            list[Document]: List of LlamaIndex Document objects with text and metadata.

        Raises:
            ElasticsearchReaderError: If loading fails after all retries.
        """
        logger.info(f"Loading documents from Elasticsearch index '{self.index}' (limit: {limit})")

        # Create reader
        reader = LlamaElasticsearchReader(endpoint=self.endpoint, index=self.index)

        # Retry logic
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                # Load documents
                docs = cast(
                    list[Document],
                    reader.load_data(
                        field="text",  # Default field to extract
                        query=query,
                        embedding_field=None,
                    ),
                )

                # Apply limit if specified
                if limit is not None:
                    docs = docs[:limit]

                # Add metadata
                for doc in docs:
                    if not doc.metadata:
                        doc.metadata = {}
                    doc.metadata["source_type"] = "elasticsearch"
                    doc.metadata["index"] = self.index

                logger.info(f"Loaded {len(docs)} documents from Elasticsearch")
                return docs

            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    backoff = 2**attempt
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.max_retries} failed: {e}. "
                        f"Retrying in {backoff}s..."
                    )
                else:
                    logger.error(f"All {self.max_retries} attempts failed: {e}")

        # All retries exhausted
        raise ElasticsearchReaderError(
            f"Failed to load Elasticsearch documents after {self.max_retries} attempts"
        ) from last_error
