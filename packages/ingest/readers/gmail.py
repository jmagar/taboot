"""Gmail reader using LlamaIndex.

Implements Gmail message ingestion via LlamaIndex GmailReader.
Per research.md: Use LlamaIndex readers for standardized Document abstraction.
"""

import logging
from typing import Optional

from llama_index.core import Document
from llama_index.readers.google import GmailReader as LlamaGmailReader

logger = logging.getLogger(__name__)


class GmailReaderError(Exception):
    """Base exception for GmailReader errors."""

    pass


class GmailReader:
    """Gmail reader using LlamaIndex GmailReader.

    Implements ingestion of email messages from Gmail using OAuth credentials.
    """

    def __init__(
        self,
        credentials_path: str,
        max_retries: int = 3,
    ) -> None:
        """Initialize GmailReader with OAuth credentials.

        Args:
            credentials_path: Path to OAuth credentials.json file.
            max_retries: Maximum number of retry attempts (default: 3).

        Raises:
            ValueError: If credentials_path is empty.
        """
        if not credentials_path:
            raise ValueError("credentials_path cannot be empty")

        self.credentials_path = credentials_path
        self.max_retries = max_retries

        logger.info(
            f"Initialized GmailReader (credentials_path={credentials_path}, max_retries={max_retries})"
        )

    def load_data(
        self, query: str = "", limit: Optional[int] = None
    ) -> list[Document]:
        """Load email messages from Gmail.

        Args:
            query: Gmail search query (e.g., 'is:unread', 'from:someone@example.com').
                   Empty query loads all messages.
            limit: Optional maximum number of messages to load.

        Returns:
            list[Document]: List of LlamaIndex Document objects with text and metadata.

        Raises:
            GmailReaderError: If loading fails after all retries.
        """
        logger.info(f"Loading Gmail messages (query: '{query}', limit: {limit})")

        # Create reader
        reader = LlamaGmailReader(credentials_path=self.credentials_path)

        # Retry logic
        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                # Load messages
                docs = reader.load_data(query=query, max_results=limit or 10)

                # Apply limit if specified
                if limit is not None:
                    docs = docs[:limit]

                # Add metadata
                for doc in docs:
                    if not doc.metadata:
                        doc.metadata = {}
                    doc.metadata["source_type"] = "gmail"
                    doc.metadata["query"] = query

                logger.info(f"Loaded {len(docs)} email documents")
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
        raise GmailReaderError(
            f"Failed to load Gmail messages after {self.max_retries} attempts"
        ) from last_error
