"""Reddit reader using LlamaIndex.

Implements Reddit post and comment ingestion via LlamaIndex RedditReader.
Per research.md: Use LlamaIndex readers for standardized Document abstraction.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from llama_index.core import Document
from llama_index.readers.reddit import RedditReader as LlamaRedditReader

from packages.schemas.reddit import RedditComment, RedditPost, Subreddit

logger = logging.getLogger(__name__)

# Extractor version for all Reddit entities
EXTRACTOR_VERSION = "1.0.0"


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

        Notes:
            LlamaIndex RedditReader requires environment variables:
            - REDDIT_CLIENT_ID
            - REDDIT_CLIENT_SECRET
            - REDDIT_USER_AGENT
        """
        if not subreddit:
            raise ValueError("subreddit cannot be empty")

        logger.info(f"Loading data from subreddit r/{subreddit} (limit: {limit})")

        # Set environment variables for LlamaIndex RedditReader
        import os

        os.environ["REDDIT_CLIENT_ID"] = self.client_id
        os.environ["REDDIT_CLIENT_SECRET"] = self.client_secret
        os.environ["REDDIT_USER_AGENT"] = self.user_agent

        # Create reader (no constructor arguments needed)
        reader = LlamaRedditReader()

        # Retry logic
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                # Load posts from subreddit
                docs = reader.load_data(
                    subreddits=[subreddit], search_keys=["hot"], post_limit=limit or 10
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

    def extract_entities(
        self, subreddit: str, limit: int | None = None
    ) -> dict[str, list[Subreddit] | list[RedditPost] | list[RedditComment]]:
        """Extract Subreddit, RedditPost, and RedditComment entities from Reddit.

        This method loads documents from Reddit via LlamaIndex RedditReader and
        extracts structured entities following the Phase 4 refactor pattern.

        Args:
            subreddit: Subreddit name (e.g., 'python', 'machinelearning').
            limit: Optional maximum number of posts to load.

        Returns:
            dict with keys 'subreddits', 'posts', 'comments' containing lists of extracted entities.

        Raises:
            ValueError: If subreddit is empty.
            RedditReaderError: If loading or extraction fails.
        """
        # Load documents from Reddit
        docs = self.load_data(subreddit=subreddit, limit=limit)

        # Initialize entity lists
        subreddits: list[Subreddit] = []
        posts: list[RedditPost] = []
        comments: list[RedditComment] = []

        # Track current timestamp for temporal fields
        now = datetime.now(UTC)

        # Track seen subreddits to avoid duplicates
        seen_subreddits: set[str] = set()

        # Extract entities from each document
        for doc in docs:
            if not doc.metadata:
                continue

            metadata = doc.metadata

            # Determine document type by metadata keys
            # Subreddit metadata has 'display_name' or only 'subreddit' + 'subscribers'
            if "display_name" in metadata or (
                "subreddit" in metadata
                and "subscribers" in metadata
                and "post_id" not in metadata
                and "comment_id" not in metadata
            ):
                # Extract Subreddit entity
                subreddit_name = metadata.get("subreddit", "")
                if subreddit_name and subreddit_name not in seen_subreddits:
                    try:
                        subreddit_entity = self._extract_subreddit(metadata, now)
                        subreddits.append(subreddit_entity)
                        seen_subreddits.add(subreddit_name)
                    except Exception as e:
                        logger.warning(f"Failed to extract subreddit from {doc}: {e}")

            # Post metadata has 'post_id'
            elif "post_id" in metadata:
                try:
                    post_entity = self._extract_post(metadata, now)
                    posts.append(post_entity)
                except Exception as e:
                    logger.warning(f"Failed to extract post from {doc}: {e}")

            # Comment metadata has 'comment_id'
            elif "comment_id" in metadata:
                try:
                    comment_entity = self._extract_comment(metadata, now)
                    comments.append(comment_entity)
                except Exception as e:
                    logger.warning(f"Failed to extract comment from {doc}: {e}")

        logger.info(
            f"Extracted {len(subreddits)} subreddits, {len(posts)} posts, "
            f"{len(comments)} comments from r/{subreddit}"
        )

        return {"subreddits": subreddits, "posts": posts, "comments": comments}

    def _extract_subreddit(self, metadata: dict[str, Any], now: datetime) -> Subreddit:
        """Extract Subreddit entity from document metadata.

        Args:
            metadata: Document metadata from LlamaIndex RedditReader.
            now: Current timestamp for created_at/updated_at fields.

        Returns:
            Subreddit entity with temporal tracking and extraction metadata.
        """
        # Parse created_utc timestamp if available
        created_utc = metadata.get("created_utc")
        source_timestamp = None
        if created_utc:
            if isinstance(created_utc, (int, float)):
                source_timestamp = datetime.fromtimestamp(created_utc, tz=UTC)
            elif isinstance(created_utc, datetime):
                source_timestamp = created_utc

        return Subreddit(
            # Identity fields
            name=metadata.get("subreddit", "").lower(),
            display_name=metadata.get("display_name", metadata.get("subreddit", "")),
            # Content fields (optional)
            description=metadata.get("description"),
            subscribers=metadata.get("subscribers"),
            created_utc=source_timestamp,
            over_18=metadata.get("over_18"),
            # Temporal tracking (required)
            created_at=now,
            updated_at=now,
            source_timestamp=source_timestamp,
            # Extraction metadata (required)
            extraction_tier="A",  # Reddit API = deterministic
            extraction_method="reddit_api",
            confidence=1.0,  # API data is always high confidence
            extractor_version=EXTRACTOR_VERSION,
        )

    def _extract_post(self, metadata: dict[str, Any], now: datetime) -> RedditPost:
        """Extract RedditPost entity from document metadata.

        Args:
            metadata: Document metadata from LlamaIndex RedditReader.
            now: Current timestamp for created_at/updated_at fields.

        Returns:
            RedditPost entity with temporal tracking and extraction metadata.
        """
        # Parse created_utc timestamp if available
        created_utc = metadata.get("created_utc")
        source_timestamp = None
        if created_utc:
            if isinstance(created_utc, (int, float)):
                source_timestamp = datetime.fromtimestamp(created_utc, tz=UTC)
            elif isinstance(created_utc, datetime):
                source_timestamp = created_utc

        return RedditPost(
            # Identity fields
            post_id=metadata.get("post_id", ""),
            title=metadata.get("title", ""),
            # Content fields (optional)
            selftext=metadata.get("selftext"),
            score=metadata.get("score"),
            num_comments=metadata.get("num_comments"),
            created_utc=source_timestamp,
            url=metadata.get("url"),
            permalink=metadata.get("permalink"),
            is_self=metadata.get("is_self"),
            over_18=metadata.get("over_18"),
            gilded=metadata.get("gilded"),
            # Temporal tracking (required)
            created_at=now,
            updated_at=now,
            source_timestamp=source_timestamp,
            # Extraction metadata (required)
            extraction_tier="A",
            extraction_method="reddit_api",
            confidence=1.0,
            extractor_version=EXTRACTOR_VERSION,
        )

    def _extract_comment(self, metadata: dict[str, Any], now: datetime) -> RedditComment:
        """Extract RedditComment entity from document metadata.

        Args:
            metadata: Document metadata from LlamaIndex RedditReader.
            now: Current timestamp for created_at/updated_at fields.

        Returns:
            RedditComment entity with temporal tracking and extraction metadata.
        """
        # Parse created_utc timestamp if available
        created_utc = metadata.get("created_utc")
        source_timestamp = None
        if created_utc:
            if isinstance(created_utc, (int, float)):
                source_timestamp = datetime.fromtimestamp(created_utc, tz=UTC)
            elif isinstance(created_utc, datetime):
                source_timestamp = created_utc

        return RedditComment(
            # Identity fields
            comment_id=metadata.get("comment_id", ""),
            body=metadata.get("body", ""),
            # Content fields (optional)
            score=metadata.get("score"),
            created_utc=source_timestamp,
            permalink=metadata.get("permalink"),
            parent_id=metadata.get("parent_id"),
            depth=metadata.get("depth"),
            gilded=metadata.get("gilded"),
            edited=metadata.get("edited"),
            # Temporal tracking (required)
            created_at=now,
            updated_at=now,
            source_timestamp=source_timestamp,
            # Extraction metadata (required)
            extraction_tier="A",
            extraction_method="reddit_api",
            confidence=1.0,
            extractor_version=EXTRACTOR_VERSION,
        )
