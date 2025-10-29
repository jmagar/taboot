"""PersonWriter - Batched Neo4j writer for Person entities.

Implements GraphWriterPort using batched UNWIND operations for high throughput.
Follows the pattern from packages/graph/writers/swag_writer.py.

Performance target: ≥20k edges/min with 2k-row UNWIND batches.
"""

import logging

from packages.graph.client import Neo4jClient
from packages.schemas.core.person import Person

logger = logging.getLogger(__name__)


class PersonWriter:
    """Batched Neo4j writer for Person entity ingestion.

    Implements GraphWriterPort interface using batched UNWIND operations.
    Ensures atomic writes and high throughput (target ≥20k edges/min).

    Attributes:
        neo4j_client: Neo4j client instance with connection pooling.
        batch_size: Number of rows per UNWIND batch (default 2000).
    """

    def __init__(self, neo4j_client: Neo4jClient, batch_size: int = 2000) -> None:
        """Initialize PersonWriter with Neo4j client.

        Args:
            neo4j_client: Neo4j client instance (must be connected).
            batch_size: Number of rows per UNWIND batch (default 2000).
        """
        self.neo4j_client = neo4j_client
        self.batch_size = batch_size

        logger.info(f"Initialized PersonWriter (batch_size={batch_size})")

    def write_persons(self, persons: list[Person]) -> dict[str, int]:
        """Write Person nodes to Neo4j using batched UNWIND.

        Creates or updates Person nodes with all properties.
        Uses MERGE on unique key (email) for idempotency.

        Args:
            persons: List of Person entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total persons written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If persons list contains invalid data.
            Exception: If Neo4j write operation fails.
        """
        if not persons:
            logger.info("No persons to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare person parameters (optimized list comprehension)
        try:
            person_params = [
                {
                    "name": p.name,
                    "email": p.email,
                    "role": p.role,
                    "bio": p.bio,
                    "github_username": p.github_username,
                    "reddit_username": p.reddit_username,
                    "youtube_channel": p.youtube_channel,
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
                for p in persons
            ]
        except AttributeError as e:
            logger.error(f"Invalid Person entity in batch: {e}")
            raise ValueError(f"Invalid Person entity: {e}") from e

        # Execute in batches
        try:
            with self.neo4j_client.session() as session:
                for i in range(0, len(person_params), self.batch_size):
                    batch = person_params[i : i + self.batch_size]

                    # Optimized Cypher query with explicit property setting
                    query = """
                    UNWIND $rows AS row
                    MERGE (p:Person {email: row.email})
                    ON CREATE SET p.created_at = row.created_at
                    SET p.name = row.name,
                        p.role = row.role,
                        p.bio = row.bio,
                        p.github_username = row.github_username,
                        p.reddit_username = row.reddit_username,
                        p.youtube_channel = row.youtube_channel,
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
                        f"Wrote person batch {batches_executed}: "
                        f"{len(batch)} rows, "
                        f"counters={summary.counters}"
                    )

            logger.info(f"Wrote {total_written} Person node(s) in {batches_executed} batch(es)")

            return {"total_written": total_written, "batches_executed": batches_executed}

        except Exception as e:
            logger.error(
                f"Failed to write persons to Neo4j: {e}",
                extra={"batch_size": self.batch_size, "total_persons": len(persons)},
            )
            raise


# Export public API
__all__ = ["PersonWriter"]
