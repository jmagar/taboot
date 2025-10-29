"""RedditWriter - Batched Neo4j writer for Reddit entities.

Implements GraphWriterPort using batched UNWIND operations for high throughput.
Handles Subreddit, RedditPost, and RedditComment entities with relationships.

Performance target: ≥20k edges/min with 2k-row UNWIND batches.
"""

import logging
from datetime import datetime

from packages.graph.client import Neo4jClient
from packages.schemas.reddit import RedditComment, RedditPost, Subreddit

logger = logging.getLogger(__name__)


class RedditWriter:
    """Batched Neo4j writer for Reddit entity ingestion.

    Implements GraphWriterPort interface using batched UNWIND operations.
    Ensures atomic writes and high throughput (target ≥20k edges/min).

    Attributes:
        neo4j_client: Neo4j client instance with connection pooling.
        batch_size: Number of rows per UNWIND batch (default 2000).
    """

    def __init__(self, neo4j_client: Neo4jClient, batch_size: int = 2000) -> None:
        """Initialize RedditWriter with Neo4j client.

        Args:
            neo4j_client: Neo4j client instance (must be connected).
            batch_size: Number of rows per UNWIND batch (default 2000).
        """
        self.neo4j_client = neo4j_client
        self.batch_size = batch_size

        logger.info(f"Initialized RedditWriter (batch_size={batch_size})")

    def write_subreddits(self, subreddits: list[Subreddit]) -> dict[str, int]:
        """Write Subreddit nodes to Neo4j using batched UNWIND.

        Creates or updates Subreddit nodes with all properties.
        Uses MERGE on unique key (name) for idempotency.

        Args:
            subreddits: List of Subreddit entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total subreddits written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If subreddits list contains invalid data.
            Exception: If Neo4j write operation fails.
        """
        if not subreddits:
            logger.info("No subreddits to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare subreddit parameters
        try:
            subreddit_params = [
                {
                    "name": s.name,
                    "display_name": s.display_name,
                    "description": s.description,
                    "subscribers": s.subscribers,
                    "created_utc": s.created_utc.isoformat() if s.created_utc else None,
                    "over_18": s.over_18,
                    "created_at": s.created_at.isoformat(),
                    "updated_at": s.updated_at.isoformat(),
                    "source_timestamp": (
                        s.source_timestamp.isoformat() if s.source_timestamp else None
                    ),
                    "extraction_tier": s.extraction_tier,
                    "extraction_method": s.extraction_method,
                    "confidence": s.confidence,
                    "extractor_version": s.extractor_version,
                }
                for s in subreddits
            ]
        except AttributeError as e:
            logger.error(f"Invalid Subreddit entity in batch: {e}")
            raise ValueError(f"Invalid Subreddit entity: {e}") from e

        # Execute in batches
        try:
            with self.neo4j_client.session() as session:
                for i in range(0, len(subreddit_params), self.batch_size):
                    batch = subreddit_params[i : i + self.batch_size]

                    query = """
                    UNWIND $rows AS row
                    MERGE (s:Subreddit {name: row.name})
                    SET s.display_name = row.display_name,
                        s.description = row.description,
                        s.subscribers = row.subscribers,
                        s.created_utc = row.created_utc,
                        s.over_18 = row.over_18,
                        s.created_at = row.created_at,
                        s.updated_at = row.updated_at,
                        s.source_timestamp = row.source_timestamp,
                        s.extraction_tier = row.extraction_tier,
                        s.extraction_method = row.extraction_method,
                        s.confidence = row.confidence,
                        s.extractor_version = row.extractor_version
                    RETURN count(s) AS created_count
                    """

                    result = session.run(query, {"rows": batch})
                    summary = result.consume()

                    total_written += len(batch)
                    batches_executed += 1

                    logger.debug(
                        f"Wrote subreddit batch {batches_executed}: "
                        f"{len(batch)} rows, "
                        f"counters={summary.counters}"
                    )

            logger.info(
                f"Wrote {total_written} Subreddit node(s) in {batches_executed} batch(es)"
            )

            return {"total_written": total_written, "batches_executed": batches_executed}

        except Exception as e:
            logger.error(
                f"Failed to write subreddits to Neo4j: {e}",
                extra={"batch_size": self.batch_size, "total_subreddits": len(subreddits)},
            )
            raise

    def write_posts(self, posts: list[RedditPost]) -> dict[str, int]:
        """Write RedditPost nodes to Neo4j using batched UNWIND.

        Creates or updates RedditPost nodes with all properties.
        Uses MERGE on unique key (post_id) for idempotency.

        Args:
            posts: List of RedditPost entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total posts written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If posts list contains invalid data.
            Exception: If Neo4j write operation fails.
        """
        if not posts:
            logger.info("No posts to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare post parameters
        try:
            post_params = [
                {
                    "post_id": p.post_id,
                    "title": p.title,
                    "selftext": p.selftext,
                    "score": p.score,
                    "num_comments": p.num_comments,
                    "created_utc": p.created_utc.isoformat() if p.created_utc else None,
                    "url": p.url,
                    "permalink": p.permalink,
                    "is_self": p.is_self,
                    "over_18": p.over_18,
                    "gilded": p.gilded,
                    "created_at": p.created_at.isoformat(),
                    "updated_at": p.updated_at.isoformat(),
                    "source_timestamp": (
                        p.source_timestamp.isoformat() if p.source_timestamp else None
                    ),
                    "extraction_tier": p.extraction_tier,
                    "extraction_method": p.extraction_method,
                    "confidence": p.confidence,
                    "extractor_version": p.extractor_version,
                }
                for p in posts
            ]
        except AttributeError as e:
            logger.error(f"Invalid RedditPost entity in batch: {e}")
            raise ValueError(f"Invalid RedditPost entity: {e}") from e

        # Execute in batches
        try:
            with self.neo4j_client.session() as session:
                for i in range(0, len(post_params), self.batch_size):
                    batch = post_params[i : i + self.batch_size]

                    query = """
                    UNWIND $rows AS row
                    MERGE (p:RedditPost {post_id: row.post_id})
                    SET p.title = row.title,
                        p.selftext = row.selftext,
                        p.score = row.score,
                        p.num_comments = row.num_comments,
                        p.created_utc = row.created_utc,
                        p.url = row.url,
                        p.permalink = row.permalink,
                        p.is_self = row.is_self,
                        p.over_18 = row.over_18,
                        p.gilded = row.gilded,
                        p.created_at = row.created_at,
                        p.updated_at = row.updated_at,
                        p.source_timestamp = row.source_timestamp,
                        p.extraction_tier = row.extraction_tier,
                        p.extraction_method = row.extraction_method,
                        p.confidence = row.confidence,
                        p.extractor_version = row.extractor_version
                    RETURN count(p) AS created_count
                    """

                    result = session.run(query, {"rows": batch})
                    summary = result.consume()

                    total_written += len(batch)
                    batches_executed += 1

                    logger.debug(
                        f"Wrote post batch {batches_executed}: "
                        f"{len(batch)} rows, "
                        f"counters={summary.counters}"
                    )

            logger.info(f"Wrote {total_written} RedditPost node(s) in {batches_executed} batch(es)")

            return {"total_written": total_written, "batches_executed": batches_executed}

        except Exception as e:
            logger.error(
                f"Failed to write posts to Neo4j: {e}",
                extra={"batch_size": self.batch_size, "total_posts": len(posts)},
            )
            raise

    def write_comments(self, comments: list[RedditComment]) -> dict[str, int]:
        """Write RedditComment nodes to Neo4j using batched UNWIND.

        Creates or updates RedditComment nodes with all properties.
        Uses MERGE on unique key (comment_id) for idempotency.

        Args:
            comments: List of RedditComment entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total comments written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If comments list contains invalid data.
            Exception: If Neo4j write operation fails.
        """
        if not comments:
            logger.info("No comments to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare comment parameters
        try:
            comment_params = [
                {
                    "comment_id": c.comment_id,
                    "body": c.body,
                    "score": c.score,
                    "created_utc": c.created_utc.isoformat() if c.created_utc else None,
                    "permalink": c.permalink,
                    "parent_id": c.parent_id,
                    "depth": c.depth,
                    "gilded": c.gilded,
                    "edited": c.edited,
                    "created_at": c.created_at.isoformat(),
                    "updated_at": c.updated_at.isoformat(),
                    "source_timestamp": (
                        c.source_timestamp.isoformat() if c.source_timestamp else None
                    ),
                    "extraction_tier": c.extraction_tier,
                    "extraction_method": c.extraction_method,
                    "confidence": c.confidence,
                    "extractor_version": c.extractor_version,
                }
                for c in comments
            ]
        except AttributeError as e:
            logger.error(f"Invalid RedditComment entity in batch: {e}")
            raise ValueError(f"Invalid RedditComment entity: {e}") from e

        # Execute in batches
        try:
            with self.neo4j_client.session() as session:
                for i in range(0, len(comment_params), self.batch_size):
                    batch = comment_params[i : i + self.batch_size]

                    query = """
                    UNWIND $rows AS row
                    MERGE (c:RedditComment {comment_id: row.comment_id})
                    SET c.body = row.body,
                        c.score = row.score,
                        c.created_utc = row.created_utc,
                        c.permalink = row.permalink,
                        c.parent_id = row.parent_id,
                        c.depth = row.depth,
                        c.gilded = row.gilded,
                        c.edited = row.edited,
                        c.created_at = row.created_at,
                        c.updated_at = row.updated_at,
                        c.source_timestamp = row.source_timestamp,
                        c.extraction_tier = row.extraction_tier,
                        c.extraction_method = row.extraction_method,
                        c.confidence = row.confidence,
                        c.extractor_version = row.extractor_version
                    RETURN count(c) AS created_count
                    """

                    result = session.run(query, {"rows": batch})
                    summary = result.consume()

                    total_written += len(batch)
                    batches_executed += 1

                    logger.debug(
                        f"Wrote comment batch {batches_executed}: "
                        f"{len(batch)} rows, "
                        f"counters={summary.counters}"
                    )

            logger.info(
                f"Wrote {total_written} RedditComment node(s) in {batches_executed} batch(es)"
            )

            return {"total_written": total_written, "batches_executed": batches_executed}

        except Exception as e:
            logger.error(
                f"Failed to write comments to Neo4j: {e}",
                extra={"batch_size": self.batch_size, "total_comments": len(comments)},
            )
            raise

    def write_post_belongs_to_subreddit(
        self,
        post_id: str,
        subreddit_name: str,
        created_at: datetime,
        extraction_tier: str,
        extraction_method: str,
        confidence: float,
        extractor_version: str,
    ) -> dict[str, int]:
        """Create BELONGS_TO relationship from RedditPost to Subreddit.

        Args:
            post_id: Reddit post ID.
            subreddit_name: Subreddit name.
            created_at: When relationship was created.
            extraction_tier: Extraction tier (A, B, C).
            extraction_method: Method used for extraction.
            confidence: Extraction confidence (0.0-1.0).
            extractor_version: Version of extractor.

        Returns:
            dict[str, int]: Statistics with total_written count.

        Raises:
            Exception: If Neo4j write operation fails.
        """
        try:
            with self.neo4j_client.session() as session:
                query = """
                MATCH (p:RedditPost {post_id: $post_id})
                MATCH (s:Subreddit {name: $subreddit_name})
                MERGE (p)-[r:BELONGS_TO]->(s)
                SET r.created_at = $created_at,
                    r.extraction_tier = $extraction_tier,
                    r.extraction_method = $extraction_method,
                    r.confidence = $confidence,
                    r.extractor_version = $extractor_version
                RETURN count(r) AS rel_count
                """

                result = session.run(
                    query,
                    {
                        "post_id": post_id,
                        "subreddit_name": subreddit_name,
                        "created_at": created_at.isoformat(),
                        "extraction_tier": extraction_tier,
                        "extraction_method": extraction_method,
                        "confidence": confidence,
                        "extractor_version": extractor_version,
                    },
                )
                _ = result.consume()

                logger.debug(f"Created BELONGS_TO relationship: {post_id} -> {subreddit_name}")

                return {"total_written": 1}

        except Exception as e:
            logger.error(f"Failed to write BELONGS_TO relationship: {e}")
            raise

    def write_comment_replied_to(
        self,
        comment_id: str,
        parent_id: str,
        parent_type: str,
        created_at: datetime,
        extraction_tier: str,
        extraction_method: str,
        confidence: float,
        extractor_version: str,
    ) -> dict[str, int]:
        """Create REPLIED_TO relationship from RedditComment to Post or Comment.

        Args:
            comment_id: Reddit comment ID.
            parent_id: Parent post or comment ID.
            parent_type: Type of parent ('post' or 'comment').
            created_at: When relationship was created.
            extraction_tier: Extraction tier (A, B, C).
            extraction_method: Method used for extraction.
            confidence: Extraction confidence (0.0-1.0).
            extractor_version: Version of extractor.

        Returns:
            dict[str, int]: Statistics with total_written count.

        Raises:
            ValueError: If parent_type is invalid.
            Exception: If Neo4j write operation fails.
        """
        if parent_type not in ("post", "comment"):
            raise ValueError(f"Invalid parent_type: {parent_type}")

        try:
            with self.neo4j_client.session() as session:
                if parent_type == "post":
                    query = """
                    MATCH (c:RedditComment {comment_id: $comment_id})
                    MATCH (p:RedditPost {post_id: $parent_id})
                    MERGE (c)-[r:REPLIED_TO]->(p)
                    SET r.created_at = $created_at,
                        r.extraction_tier = $extraction_tier,
                        r.extraction_method = $extraction_method,
                        r.confidence = $confidence,
                        r.extractor_version = $extractor_version
                    RETURN count(r) AS rel_count
                    """
                else:  # parent_type == "comment"
                    query = """
                    MATCH (c1:RedditComment {comment_id: $comment_id})
                    MATCH (c2:RedditComment {comment_id: $parent_id})
                    MERGE (c1)-[r:REPLIED_TO]->(c2)
                    SET r.created_at = $created_at,
                        r.extraction_tier = $extraction_tier,
                        r.extraction_method = $extraction_method,
                        r.confidence = $confidence,
                        r.extractor_version = $extractor_version
                    RETURN count(r) AS rel_count
                    """

                result = session.run(
                    query,
                    {
                        "comment_id": comment_id,
                        "parent_id": parent_id,
                        "created_at": created_at.isoformat(),
                        "extraction_tier": extraction_tier,
                        "extraction_method": extraction_method,
                        "confidence": confidence,
                        "extractor_version": extractor_version,
                    },
                )
                _ = result.consume()

                logger.debug(f"Created REPLIED_TO relationship: {comment_id} -> {parent_id}")

                return {"total_written": 1}

        except Exception as e:
            logger.error(f"Failed to write REPLIED_TO relationship: {e}")
            raise


# Export public API
__all__ = ["RedditWriter"]
