"""EventWriter - Batched Neo4j writer for Event entities.

Implements GraphWriterPort using batched UNWIND operations for high throughput.
Follows the pattern from packages/graph/writers/person_writer.py.

Performance target: ≥20k edges/min with 2k-row UNWIND batches.
"""

import logging

from packages.graph.client import Neo4jClient
from packages.schemas.core.event import Event

logger = logging.getLogger(__name__)


class EventWriter:
    """Batched Neo4j writer for Event entity ingestion.

    Implements GraphWriterPort interface using batched UNWIND operations.
    Ensures atomic writes and high throughput (target ≥20k edges/min).

    Attributes:
        neo4j_client: Neo4j client instance with connection pooling.
        batch_size: Number of rows per UNWIND batch (default 2000).
    """

    def __init__(self, neo4j_client: Neo4jClient, batch_size: int = 2000) -> None:
        """Initialize EventWriter with Neo4j client.

        Args:
            neo4j_client: Neo4j client instance (must be connected).
            batch_size: Number of rows per UNWIND batch (default 2000).
        """
        self.neo4j_client = neo4j_client
        self.batch_size = batch_size

        logger.info(f"Initialized EventWriter (batch_size={batch_size})")

    def write_events(self, events: list[Event]) -> dict[str, int]:
        """Write Event nodes to Neo4j using batched UNWIND.

        Creates or updates Event nodes with all properties.
        Uses MERGE on unique key (name) for idempotency.

        Args:
            events: List of Event entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total events written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If events list contains invalid data.
            Exception: If Neo4j write operation fails.
        """
        if not events:
            logger.info("No events to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare event parameters (optimized list comprehension)
        try:
            event_params = [
                {
                    "name": e.name,
                    "start_time": e.start_time.isoformat() if e.start_time else None,
                    "end_time": e.end_time.isoformat() if e.end_time else None,
                    "location": e.location,
                    "event_type": e.event_type,
                    "created_at": e.created_at.isoformat(),
                    "updated_at": e.updated_at.isoformat(),
                    "source_timestamp": (
                        e.source_timestamp.isoformat() if e.source_timestamp else None
                    ),
                    "extraction_tier": e.extraction_tier,
                    "extraction_method": e.extraction_method,
                    "confidence": e.confidence,
                    "extractor_version": e.extractor_version,
                }
                for e in events
            ]
        except AttributeError as e:
            logger.error(f"Invalid Event entity in batch: {e}")
            raise ValueError(f"Invalid Event entity: {e}") from e

        # Execute in batches
        try:
            with self.neo4j_client.session() as session:
                for i in range(0, len(event_params), self.batch_size):
                    batch = event_params[i : i + self.batch_size]

                    # Optimized Cypher query with explicit property setting
                    query = """
                    UNWIND $rows AS row
                    MERGE (e:Event {name: row.name})
                    SET e.start_time = row.start_time,
                        e.end_time = row.end_time,
                        e.location = row.location,
                        e.event_type = row.event_type,
                        e.created_at = row.created_at,
                        e.updated_at = row.updated_at,
                        e.source_timestamp = row.source_timestamp,
                        e.extraction_tier = row.extraction_tier,
                        e.extraction_method = row.extraction_method,
                        e.confidence = row.confidence,
                        e.extractor_version = row.extractor_version
                    RETURN count(e) AS created_count
                    """

                    result = session.run(query, {"rows": batch})
                    summary = result.consume()

                    total_written += len(batch)
                    batches_executed += 1

                    logger.debug(
                        f"Wrote event batch {batches_executed}: "
                        f"{len(batch)} rows, "
                        f"counters={summary.counters}"
                    )

            logger.info(f"Wrote {total_written} Event node(s) in {batches_executed} batch(es)")

            return {"total_written": total_written, "batches_executed": batches_executed}

        except Exception as e:
            logger.error(
                f"Failed to write events to Neo4j: {e}",
                extra={"batch_size": self.batch_size, "total_events": len(events)},
            )
            raise


# Export public API
__all__ = ["EventWriter"]
