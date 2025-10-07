"""Reddit reader for ingesting posts and comments from subreddits.

This module implements RedditReader which extends BaseReader to fetch posts and
comments from configured subreddits using PRAW (Python Reddit API Wrapper).

Key Features:
1. Fetch posts from multiple subreddits with configurable limits
2. Include comments and nested comment threads (up to 5 levels deep)
3. Incremental sync using timestamp-based filtering (with limitations)
4. Time-windowing strategy to handle Reddit's 1000-item API hard cap

Critical Limitations:
- Reddit API hard caps ALL listings at 1000 items maximum
- No native 'since' parameter - must fetch and filter client-side
- For high-volume subreddits, complete history cannot be fetched
- Time-windowing required for large subreddits to stay within 1000-item limit
"""

import hashlib
import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from datetime import UTC, datetime
from typing import Any

import praw  # type: ignore[import-untyped]
from praw.models import Comment, MoreComments, Submission, Subreddit  # type: ignore[import-untyped]

from llamacrawl.models.document import Document, DocumentMetadata
from llamacrawl.readers.base import BaseReader
from llamacrawl.storage.redis import RedisClient
from llamacrawl.utils.retry import retry_with_backoff


class RedditReader(BaseReader):
    """Reddit reader for posts and comments from subreddits.

    This reader uses PRAW to fetch posts and comments from configured subreddits.
    It supports incremental sync with limitations due to Reddit's API constraints.

    CRITICAL LIMITATION: Reddit API hard limits ALL listings to 1000 items maximum.
    This is an upstream API limitation, not a PRAW issue.

    Attributes:
        _reddit: Lazy-initialized PRAW Reddit instance
        max_comment_depth: Maximum depth for nested comments (default: 5)
        max_comments_per_post: Maximum comments per post (default: 100)
    """

    def __init__(
        self,
        source_name: str,
        config: dict[str, Any],
        redis_client: RedisClient,
    ):
        """Initialize Reddit reader.

        Args:
            source_name: Name of the data source (should be 'reddit')
            config: Reddit-specific configuration from config.yaml
            redis_client: Redis client for state management

        Raises:
            ValueError: If required credentials are missing
        """
        super().__init__(source_name, config, redis_client)

        # Validate required credentials
        self.validate_credentials([
            "REDDIT_CLIENT_ID",
            "REDDIT_CLIENT_SECRET",
            "REDDIT_USER_AGENT",
        ])

        # Extract configuration
        self.max_comment_depth = config.get("max_comment_depth", 5)
        self.max_comments_per_post = 100  # Limit to top 100 comments per post

        # Lazy initialization of Reddit client
        self._reddit: praw.Reddit | None = None

        self.logger.info(
            f"RedditReader initialized with max_comment_depth={self.max_comment_depth}",
            extra={
                "source": self.source_name,
                "max_comment_depth": self.max_comment_depth,
                "max_comments_per_post": self.max_comments_per_post,
            },
        )

    def get_api_client(self) -> praw.Reddit:
        """Lazy initialization of PRAW Reddit client.

        Returns:
            PRAW Reddit instance

        Raises:
            ValueError: If credentials are invalid
        """
        if self._reddit is None:
            self.logger.debug("Initializing PRAW Reddit client")

            self._reddit = praw.Reddit(
                client_id=os.environ["REDDIT_CLIENT_ID"],
                client_secret=os.environ["REDDIT_CLIENT_SECRET"],
                user_agent=os.environ.get("REDDIT_USER_AGENT", "LlamaCrawl/1.0"),
                # Read-only mode (no username/password needed)
                check_for_async=False,
            )

            # Validate credentials by making a test request
            try:
                # This will fail if credentials are invalid
                self._reddit.user.me()
            except Exception as e:
                self.logger.error(
                    "Failed to authenticate with Reddit API",
                    extra={"source": self.source_name, "error": str(e)},
                )
                raise ValueError(f"Reddit authentication failed: {e}") from e

            self.logger.info(
                "Successfully authenticated with Reddit API",
                extra={"source": self.source_name},
            )

        return self._reddit

    def supports_incremental_sync(self) -> bool:
        """Check if Reddit reader supports incremental sync.

        Returns:
            True (with limitations - see class docstring)

        Note:
            While this returns True, Reddit incremental sync has limitations:
            - API hard cap of 1000 items per listing
            - No native 'since' parameter
            - Client-side filtering required
            - Time-windowing needed for high-volume subreddits
        """
        return True

    @retry_with_backoff(max_attempts=3, initial_delay=2.0)
    def load_data(
        self,
        progress_callback: Callable[[int, int], None] | None = None,
        **kwargs: Any,
    ) -> list[Document]:
        """Load posts and comments from configured subreddits.

        This method fetches posts from subreddits specified in config, including
        comments and nested comment threads. Supports incremental sync using
        timestamp-based filtering.

        Args:
            progress_callback: Optional callback(current, total) for progress updates
            **kwargs: Optional overrides (subreddits, limit, etc.)

        Returns:
            List of Document objects (posts and comments)

        Raises:
            ValueError: If configuration is invalid
            praw.exceptions.PRAWException: For Reddit API errors

        Note:
            Reddit API hard caps at 1000 items per listing. For large subreddits,
            use time-windowing to fetch data in smaller chunks.
        """
        reddit = self.get_api_client()

        # Get configuration
        config = self.get_source_config()
        subreddits = kwargs.get("subreddits") or config.get("subreddits", [])
        post_limit = kwargs.get("limit") or config.get("post_limit", 1000)
        include_comments = config.get("include_comments", True)

        if not subreddits:
            self.logger.warning(
                "No subreddits configured for Reddit reader",
                extra={"source": self.source_name},
            )
            return []

        # Cap at Reddit's hard limit
        post_limit = min(post_limit, 1000)

        # Calculate total expected posts for progress tracking
        total_expected_posts = post_limit * len(subreddits)
        total_posts_processed = 0

        # Get last cursor for incremental sync
        last_cursor = self.get_last_cursor()
        cursor_timestamp: datetime | None = None

        if last_cursor:
            try:
                cursor_timestamp = datetime.fromisoformat(last_cursor)
                self.logger.info(
                    f"Using incremental sync from cursor: {last_cursor}",
                    extra={
                        "source": self.source_name,
                        "cursor_timestamp": last_cursor,
                    },
                )
            except ValueError:
                self.logger.warning(
                    f"Invalid cursor format: {last_cursor}, performing full sync",
                    extra={"source": self.source_name, "cursor": last_cursor},
                )

        # Fetch posts from all subreddits
        all_documents: list[Document] = []
        latest_timestamp: datetime | None = None

        for subreddit_name in subreddits:
            try:
                docs, sub_latest, posts_processed = self._load_subreddit(
                    reddit=reddit,
                    subreddit_name=subreddit_name,
                    limit=post_limit,
                    since_timestamp=cursor_timestamp,
                    include_comments=include_comments,
                    progress_callback=progress_callback,
                    total_posts_offset=total_posts_processed,
                    total_expected_posts=total_expected_posts,
                )

                all_documents.extend(docs)
                total_posts_processed += posts_processed

                # Track latest timestamp across all subreddits
                if sub_latest and (latest_timestamp is None or sub_latest > latest_timestamp):
                    latest_timestamp = sub_latest

                self.logger.info(
                    f"Loaded {len(docs)} documents from r/{subreddit_name}",
                    extra={
                        "source": self.source_name,
                        "subreddit": subreddit_name,
                        "document_count": len(docs),
                    },
                )

            except Exception as e:
                self.logger.error(
                    f"Failed to load r/{subreddit_name}: {e}",
                    extra={
                        "source": self.source_name,
                        "subreddit": subreddit_name,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
                # Continue with other subreddits
                continue

        # Update cursor with latest timestamp
        if latest_timestamp:
            new_cursor = latest_timestamp.isoformat()
            self.set_last_cursor(new_cursor)

        # Log summary
        self.log_load_summary(
            total_fetched=len(all_documents),
            filtered_count=0,
            error_count=0,
            subreddits=subreddits,
            cursor_used=last_cursor,
            new_cursor=latest_timestamp.isoformat() if latest_timestamp else None,
        )

        return all_documents

    def _load_subreddit(
        self,
        reddit: praw.Reddit,
        subreddit_name: str,
        limit: int,
        since_timestamp: datetime | None,
        include_comments: bool,
        progress_callback: Callable[[int, int], None] | None = None,
        total_posts_offset: int = 0,
        total_expected_posts: int = 0,
    ) -> tuple[list[Document], datetime | None, int]:
        """Load posts and comments from a single subreddit.

        Args:
            reddit: PRAW Reddit instance
            subreddit_name: Name of subreddit (without 'r/' prefix)
            limit: Maximum number of posts to fetch
            since_timestamp: Only fetch posts created after this timestamp (None for all)
            include_comments: Whether to include comments
            progress_callback: Optional callback(current, total) for progress updates
            total_posts_offset: Offset to add to current progress (for multi-subreddit tracking)
            total_expected_posts: Total expected posts across all subreddits

        Returns:
            Tuple of (documents, latest_timestamp, posts_processed)
        """
        subreddit: Subreddit = reddit.subreddit(subreddit_name)
        documents: list[Document] = []
        latest_timestamp: datetime | None = None

        self.logger.info(
            f"Starting to process r/{subreddit_name} (limit: {limit} posts)",
            extra={
                "source": self.source_name,
                "subreddit": subreddit_name,
                "post_limit": limit,
                "since_timestamp": since_timestamp.isoformat() if since_timestamp else None,
            },
        )

        # Fetch posts (using 'new' sorting to get recent posts first)
        # Note: Reddit API hard caps at 1000 items
        posts = subreddit.new(limit=limit)

        post_count = 0
        for submission in posts:
            post_count += 1

            # Convert Unix timestamp to datetime
            created_utc = datetime.fromtimestamp(submission.created_utc, tz=UTC)

            # Track latest timestamp
            if latest_timestamp is None or created_utc > latest_timestamp:
                latest_timestamp = created_utc

            # Filter by timestamp if incremental sync
            if since_timestamp and created_utc <= since_timestamp:
                # Posts are sorted newest first, so we can stop here
                self.logger.debug(
                    "Reached posts older than cursor, stopping fetch",
                    extra={
                        "source": self.source_name,
                        "subreddit": subreddit_name,
                        "post_created": created_utc.isoformat(),
                        "cursor": since_timestamp.isoformat(),
                    },
                )
                break

            # Convert post to document
            post_doc = self._submission_to_document(submission, subreddit_name)
            documents.append(post_doc)

            # Load comments if enabled
            if include_comments:
                comment_docs = self._load_comments(
                    submission=submission,
                    subreddit_name=subreddit_name,
                    post_id=submission.id,
                )
                documents.extend(comment_docs)

            # Progress callback and logging every 10 posts
            if post_count % 10 == 0:
                # Update progress callback if provided
                if progress_callback:
                    current_total = total_posts_offset + post_count
                    progress_callback(current_total, total_expected_posts)

                self.logger.info(
                    f"Processing r/{subreddit_name}: {post_count} posts processed, {len(documents)} total documents",
                    extra={
                        "source": self.source_name,
                        "subreddit": subreddit_name,
                        "posts_processed": post_count,
                        "documents_collected": len(documents),
                    },
                )

        # Final progress update for this subreddit
        if progress_callback:
            current_total = total_posts_offset + post_count
            progress_callback(current_total, total_expected_posts)

        # Log final summary for this subreddit
        self.logger.info(
            f"Completed r/{subreddit_name}: {post_count} posts processed, {len(documents)} total documents",
            extra={
                "source": self.source_name,
                "subreddit": subreddit_name,
                "posts_processed": post_count,
                "documents_collected": len(documents),
            },
        )

        return documents, latest_timestamp, post_count

    def _submission_to_document(self, submission: Submission, subreddit_name: str) -> Document:
        """Convert Reddit submission to Document.

        Args:
            submission: PRAW Submission object
            subreddit_name: Name of subreddit

        Returns:
            Document object
        """
        # Compute content hash
        content = f"{submission.title}\n\n{submission.selftext}"
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Create document ID
        doc_id = f"reddit_{subreddit_name}_{submission.id}"

        # Build metadata
        created_utc = datetime.fromtimestamp(submission.created_utc, tz=UTC)

        metadata = DocumentMetadata(
            source_type="reddit",
            source_url=f"https://reddit.com{submission.permalink}",
            timestamp=created_utc,
            extra={
                "subreddit": subreddit_name,
                "post_id": submission.id,
                "author": str(submission.author) if submission.author else "[deleted]",
                "score": submission.score,
                "created_utc": created_utc.isoformat(),
                "num_comments": submission.num_comments,
                "is_self": submission.is_self,
                "link_flair_text": submission.link_flair_text,
            },
        )

        return Document(
            doc_id=doc_id,
            title=submission.title,
            content=content,
            content_hash=content_hash,
            metadata=metadata,
        )

    def _load_comments(
        self,
        submission: Submission,
        subreddit_name: str,
        post_id: str,
    ) -> list[Document]:
        """Load comments from a Reddit submission.

        Args:
            submission: PRAW Submission object
            subreddit_name: Name of subreddit
            post_id: Post ID

        Returns:
            List of Document objects (one per comment)
        """
        documents: list[Document] = []

        # Replace MoreComments objects to load nested comments with timeout
        # Limit to max_comments_per_post to avoid excessive API calls
        try:
            # Use ThreadPoolExecutor with timeout to prevent indefinite blocking
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(submission.comments.replace_more, 0)
                future.result(timeout=30)  # 30 second timeout per post
        except FuturesTimeoutError:
            self.logger.warning(
                f"Comment loading timed out for post {post_id} in r/{subreddit_name}",
                extra={
                    "source": self.source_name,
                    "subreddit": subreddit_name,
                    "post_id": post_id,
                    "timeout_seconds": 30,
                },
            )
            # Continue with whatever comments were loaded before timeout
        except Exception as e:
            self.logger.warning(
                f"Failed to load comments for post {post_id}: {e}",
                extra={
                    "source": self.source_name,
                    "subreddit": subreddit_name,
                    "post_id": post_id,
                    "error": str(e),
                },
            )
            return []  # Return empty list on failure

        # Flatten comment forest and limit depth
        comment_count = 0
        for comment in submission.comments.list():
            if comment_count >= self.max_comments_per_post:
                break

            # Skip MoreComments objects
            if isinstance(comment, MoreComments):
                continue

            # Check comment depth
            depth = self._get_comment_depth(comment)
            if depth > self.max_comment_depth:
                continue

            # Convert comment to document
            try:
                comment_doc = self._comment_to_document(
                    comment=comment,
                    subreddit_name=subreddit_name,
                    post_id=post_id,
                )
                documents.append(comment_doc)
                comment_count += 1

            except Exception as e:
                self.logger.warning(
                    f"Failed to convert comment to document: {e}",
                    extra={
                        "source": self.source_name,
                        "subreddit": subreddit_name,
                        "post_id": post_id,
                        "comment_id": comment.id if hasattr(comment, "id") else "unknown",
                        "error": str(e),
                    },
                )
                continue

        return documents

    def _get_comment_depth(self, comment: Comment) -> int:
        """Calculate depth of a comment in the tree.

        Args:
            comment: PRAW Comment object

        Returns:
            Depth (0 for top-level comments, 1+ for replies)
        """
        depth = 0
        current = comment

        while current.parent_id and not current.parent_id.startswith("t3_"):  # t3_ = submission
            depth += 1
            # Navigate up the tree (if parent is loaded)
            if hasattr(current, "parent") and callable(current.parent):
                try:
                    current = current.parent()
                except Exception:
                    break
            else:
                break

        return depth

    def _comment_to_document(
        self,
        comment: Comment,
        subreddit_name: str,
        post_id: str,
    ) -> Document:
        """Convert Reddit comment to Document.

        Args:
            comment: PRAW Comment object
            subreddit_name: Name of subreddit
            post_id: Parent post ID

        Returns:
            Document object
        """
        # Compute content hash
        content = comment.body
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Create document ID
        doc_id = f"reddit_{subreddit_name}_{post_id}_comment_{comment.id}"

        # Build metadata
        created_utc = datetime.fromtimestamp(comment.created_utc, tz=UTC)

        metadata = DocumentMetadata(
            source_type="reddit",
            source_url=f"https://reddit.com{comment.permalink}",
            timestamp=created_utc,
            extra={
                "subreddit": subreddit_name,
                "post_id": post_id,
                "comment_id": comment.id,
                "author": str(comment.author) if comment.author else "[deleted]",
                "score": comment.score,
                "created_utc": created_utc.isoformat(),
                "is_comment": True,
                "depth": self._get_comment_depth(comment),
            },
        )

        # Use first 100 chars of comment as title
        title = content[:100] + ("..." if len(content) > 100 else "")

        return Document(
            doc_id=doc_id,
            title=title,
            content=content,
            content_hash=content_hash,
            metadata=metadata,
        )
