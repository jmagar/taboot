"""Reddit reader using LlamaIndex.

Implements Reddit post and comment ingestion via LlamaIndex RedditReader.
Per research.md: Use LlamaIndex readers for standardized Document abstraction.
"""

import logging
from typing import cast

from llama_index.core import Document
from llama_index.readers.reddit import RedditReader as LlamaRedditReader

logger = logging.getLogger(__name__)


class RedditReaderError(Exception):
    """Base exception for RedditReader errors."""

    pass


class RedditReader:
    """Reddit reader using LlamaIndex RedditReader.

    Implements ingestion of posts and comments from subreddits.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        user_agent: str,
        max_retries: int = 3,
    ) -> None:
        """Initialize RedditReader with Reddit API credentials.

        Args:
            client_id: Reddit API client ID.
            client_secret: Reddit API client secret.
            user_agent: User agent string for Reddit API.
            max_retries: Maximum number of retry attempts (default: 3).

        Raises:
            ValueError: If any credential is empty.
        """
        if not client_id:
            raise ValueError("client_id cannot be empty")
        if not client_secret:
            raise ValueError("client_secret cannot be empty")
        if not user_agent:
            raise ValueError("user_agent cannot be empty")

        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self.max_retries = max_retries

        logger.info(f"Initialized RedditReader (max_retries={max_retries})")

    def load_data(self, subreddit: str, limit: int | None = None) -> list[Document]:
        """Load posts and comments from subreddit.

        Args:
            subreddit: Subreddit name (e.g., 'python', 'machinelearning').
            limit: Optional maximum number of posts to load.

        Returns:
            list[Document]: List of LlamaIndex Document objects with text and metadata.

        Raises:
            ValueError: If subreddit is empty.
            RedditReaderError: If loading fails after all retries.
        """
        if not subreddit:
            raise ValueError("subreddit cannot be empty")

        logger.info(f"Loading data from subreddit r/{subreddit} (limit: {limit})")

        # Create reader
        reader = LlamaRedditReader(
            client_id=self.client_id,
            client_secret=self.client_secret,
            user_agent=self.user_agent,
        )

        # Retry logic
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                # Load posts from subreddit
                docs = cast(
                    list[Document],
                    reader.load_data(
                        subreddits=[subreddit], search_keys=["hot"], post_limit=limit or 10
                    ),
                )

                # Apply limit if specified
                if limit is not None:
                    docs = docs[:limit]

                # Add metadata
                for doc in docs:
                    if not doc.metadata:
                        doc.metadata = {}
                    doc.metadata["source_type"] = "reddit"
                    doc.metadata["subreddit"] = subreddit

                logger.info(f"Loaded {len(docs)} documents from r/{subreddit}")
                return docs

            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    backoff = 2**attempt
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.max_retries} failed for r/{subreddit}: {e}. "
                        f"Retrying in {backoff}s..."
                    )
                else:
                    logger.error(f"All {self.max_retries} attempts failed for r/{subreddit}: {e}")

        # All retries exhausted
        raise RedditReaderError(
            f"Failed to load r/{subreddit} after {self.max_retries} attempts"
        ) from last_error
