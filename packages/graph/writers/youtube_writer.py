"""YouTubeWriter - Batched Neo4j writer for YouTube entities.

Implements GraphWriterPort using batched UNWIND operations for high throughput.
Handles Video, Channel, and Transcript entities with relationships.

Performance target: ≥20k edges/min with 2k-row UNWIND batches.
"""

import logging
from datetime import datetime

from packages.graph.client import Neo4jClient
from packages.schemas.youtube import Channel, Transcript, Video

logger = logging.getLogger(__name__)


class YouTubeWriter:
    """Batched Neo4j writer for YouTube entity ingestion.

    Implements GraphWriterPort interface using batched UNWIND operations.
    Ensures atomic writes and high throughput (target ≥20k edges/min).

    Attributes:
        neo4j_client: Neo4j client instance with connection pooling.
        batch_size: Number of rows per UNWIND batch (default 2000).
    """

    def __init__(self, neo4j_client: Neo4jClient, batch_size: int = 2000) -> None:
        """Initialize YouTubeWriter with Neo4j client.

        Args:
            neo4j_client: Neo4j client instance (must be connected).
            batch_size: Number of rows per UNWIND batch (default 2000).
        """
        self.neo4j_client = neo4j_client
        self.batch_size = batch_size

        logger.info(f"Initialized YouTubeWriter (batch_size={batch_size})")

    def write_channels(self, channels: list[Channel]) -> dict[str, int]:
        """Write Channel nodes to Neo4j using batched UNWIND.

        Creates or updates Channel nodes with all properties.
        Uses MERGE on unique key (channel_id) for idempotency.

        Args:
            channels: List of Channel entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total channels written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If channels list contains invalid data.
            Exception: If Neo4j write operation fails.
        """
        if not channels:
            logger.info("No channels to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare channel parameters
        try:
            channel_params = [
                {
                    "channel_id": c.channel_id,
                    "channel_name": c.channel_name,
                    "channel_url": c.channel_url,
                    "subscribers": c.subscribers,
                    "verified": c.verified,
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
                for c in channels
            ]
        except AttributeError as e:
            logger.error(f"Invalid Channel entity in batch: {e}")
            raise ValueError(f"Invalid Channel entity: {e}") from e

        # Execute in batches
        try:
            with self.neo4j_client.session() as session:
                for i in range(0, len(channel_params), self.batch_size):
                    batch = channel_params[i : i + self.batch_size]

                    query = """
                    UNWIND $rows AS row
                    MERGE (c:Channel {channel_id: row.channel_id})
                    SET c.channel_name = row.channel_name,
                        c.channel_url = row.channel_url,
                        c.subscribers = row.subscribers,
                        c.verified = row.verified,
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
                        f"Wrote channel batch {batches_executed}: "
                        f"{len(batch)} rows, "
                        f"counters={summary.counters}"
                    )

            logger.info(f"Wrote {total_written} Channel node(s) in {batches_executed} batch(es)")

            return {"total_written": total_written, "batches_executed": batches_executed}

        except Exception as e:
            logger.error(
                f"Failed to write channels to Neo4j: {e}",
                extra={"batch_size": self.batch_size, "total_channels": len(channels)},
            )
            raise

    def write_videos(self, videos: list[Video]) -> dict[str, int]:
        """Write Video nodes to Neo4j using batched UNWIND.

        Creates or updates Video nodes with all properties.
        Uses MERGE on unique key (video_id) for idempotency.

        Args:
            videos: List of Video entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total videos written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If videos list contains invalid data.
            Exception: If Neo4j write operation fails.
        """
        if not videos:
            logger.info("No videos to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare video parameters
        try:
            video_params = [
                {
                    "video_id": v.video_id,
                    "title": v.title,
                    "url": v.url,
                    "duration": v.duration,
                    "views": v.views,
                    "published_at": v.published_at.isoformat(),
                    "description": v.description,
                    "language": v.language,
                    "created_at": v.created_at.isoformat(),
                    "updated_at": v.updated_at.isoformat(),
                    "source_timestamp": (
                        v.source_timestamp.isoformat() if v.source_timestamp else None
                    ),
                    "extraction_tier": v.extraction_tier,
                    "extraction_method": v.extraction_method,
                    "confidence": v.confidence,
                    "extractor_version": v.extractor_version,
                }
                for v in videos
            ]
        except AttributeError as e:
            logger.error(f"Invalid Video entity in batch: {e}")
            raise ValueError(f"Invalid Video entity: {e}") from e

        # Execute in batches
        try:
            with self.neo4j_client.session() as session:
                for i in range(0, len(video_params), self.batch_size):
                    batch = video_params[i : i + self.batch_size]

                    query = """
                    UNWIND $rows AS row
                    MERGE (v:Video {video_id: row.video_id})
                    SET v.title = row.title,
                        v.url = row.url,
                        v.duration = row.duration,
                        v.views = row.views,
                        v.published_at = row.published_at,
                        v.description = row.description,
                        v.language = row.language,
                        v.created_at = row.created_at,
                        v.updated_at = row.updated_at,
                        v.source_timestamp = row.source_timestamp,
                        v.extraction_tier = row.extraction_tier,
                        v.extraction_method = row.extraction_method,
                        v.confidence = row.confidence,
                        v.extractor_version = row.extractor_version
                    RETURN count(v) AS created_count
                    """

                    result = session.run(query, {"rows": batch})
                    summary = result.consume()

                    total_written += len(batch)
                    batches_executed += 1

                    logger.debug(
                        f"Wrote video batch {batches_executed}: "
                        f"{len(batch)} rows, "
                        f"counters={summary.counters}"
                    )

            logger.info(f"Wrote {total_written} Video node(s) in {batches_executed} batch(es)")

            return {"total_written": total_written, "batches_executed": batches_executed}

        except Exception as e:
            logger.error(
                f"Failed to write videos to Neo4j: {e}",
                extra={"batch_size": self.batch_size, "total_videos": len(videos)},
            )
            raise

    def write_transcripts(self, transcripts: list[Transcript]) -> dict[str, int]:
        """Write Transcript nodes to Neo4j using batched UNWIND.

        Creates or updates Transcript nodes with all properties.
        Uses MERGE on unique key (transcript_id) for idempotency.

        Args:
            transcripts: List of Transcript entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total transcripts written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If transcripts list contains invalid data.
            Exception: If Neo4j write operation fails.
        """
        if not transcripts:
            logger.info("No transcripts to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare transcript parameters
        try:
            transcript_params = [
                {
                    "transcript_id": t.transcript_id,
                    "video_id": t.video_id,
                    "language": t.language,
                    "auto_generated": t.auto_generated,
                    "content": t.content,
                    "created_at": t.created_at.isoformat(),
                    "updated_at": t.updated_at.isoformat(),
                    "source_timestamp": (
                        t.source_timestamp.isoformat() if t.source_timestamp else None
                    ),
                    "extraction_tier": t.extraction_tier,
                    "extraction_method": t.extraction_method,
                    "confidence": t.confidence,
                    "extractor_version": t.extractor_version,
                }
                for t in transcripts
            ]
        except AttributeError as e:
            logger.error(f"Invalid Transcript entity in batch: {e}")
            raise ValueError(f"Invalid Transcript entity: {e}") from e

        # Execute in batches
        try:
            with self.neo4j_client.session() as session:
                for i in range(0, len(transcript_params), self.batch_size):
                    batch = transcript_params[i : i + self.batch_size]

                    query = """
                    UNWIND $rows AS row
                    MERGE (t:Transcript {transcript_id: row.transcript_id})
                    SET t.video_id = row.video_id,
                        t.language = row.language,
                        t.auto_generated = row.auto_generated,
                        t.content = row.content,
                        t.created_at = row.created_at,
                        t.updated_at = row.updated_at,
                        t.source_timestamp = row.source_timestamp,
                        t.extraction_tier = row.extraction_tier,
                        t.extraction_method = row.extraction_method,
                        t.confidence = row.confidence,
                        t.extractor_version = row.extractor_version
                    RETURN count(t) AS created_count
                    """

                    result = session.run(query, {"rows": batch})
                    summary = result.consume()

                    total_written += len(batch)
                    batches_executed += 1

                    logger.debug(
                        f"Wrote transcript batch {batches_executed}: "
                        f"{len(batch)} rows, "
                        f"counters={summary.counters}"
                    )

            logger.info(
                f"Wrote {total_written} Transcript node(s) in {batches_executed} batch(es)"
            )

            return {"total_written": total_written, "batches_executed": batches_executed}

        except Exception as e:
            logger.error(
                f"Failed to write transcripts to Neo4j: {e}",
                extra={"batch_size": self.batch_size, "total_transcripts": len(transcripts)},
            )
            raise

    def write_video_uploaded_by_channel(
        self,
        video_id: str,
        channel_id: str,
        created_at: datetime,
        extraction_tier: str,
        extraction_method: str,
        confidence: float,
        extractor_version: str,
    ) -> dict[str, int]:
        """Create UPLOADED_BY relationship from Video to Channel.

        Args:
            video_id: YouTube video ID.
            channel_id: YouTube channel ID.
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
                MATCH (v:Video {video_id: $video_id})
                MATCH (c:Channel {channel_id: $channel_id})
                MERGE (v)-[r:UPLOADED_BY]->(c)
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
                        "video_id": video_id,
                        "channel_id": channel_id,
                        "created_at": created_at.isoformat(),
                        "extraction_tier": extraction_tier,
                        "extraction_method": extraction_method,
                        "confidence": confidence,
                        "extractor_version": extractor_version,
                    },
                )
                _ = result.consume()

                logger.debug(f"Created UPLOADED_BY relationship: {video_id} -> {channel_id}")

                return {"total_written": 1}

        except Exception as e:
            logger.error(f"Failed to write UPLOADED_BY relationship: {e}")
            raise

    def write_video_has_transcript(
        self,
        video_id: str,
        transcript_id: str,
        created_at: datetime,
        extraction_tier: str,
        extraction_method: str,
        confidence: float,
        extractor_version: str,
    ) -> dict[str, int]:
        """Create HAS_TRANSCRIPT relationship from Video to Transcript.

        Args:
            video_id: YouTube video ID.
            transcript_id: Transcript ID.
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
                MATCH (v:Video {video_id: $video_id})
                MATCH (t:Transcript {transcript_id: $transcript_id})
                MERGE (v)-[r:HAS_TRANSCRIPT]->(t)
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
                        "video_id": video_id,
                        "transcript_id": transcript_id,
                        "created_at": created_at.isoformat(),
                        "extraction_tier": extraction_tier,
                        "extraction_method": extraction_method,
                        "confidence": confidence,
                        "extractor_version": extractor_version,
                    },
                )
                _ = result.consume()

                logger.debug(f"Created HAS_TRANSCRIPT relationship: {video_id} -> {transcript_id}")

                return {"total_written": 1}

        except Exception as e:
            logger.error(f"Failed to write HAS_TRANSCRIPT relationship: {e}")
            raise


# Export public API
__all__ = ["YouTubeWriter"]
