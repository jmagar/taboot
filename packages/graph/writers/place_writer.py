"""PlaceWriter - Batched Neo4j writer for Place entities.

Implements GraphWriterPort using batched UNWIND operations for high throughput.
Follows the pattern from packages/graph/writers/person_writer.py.

Performance target: ≥20k edges/min with 2k-row UNWIND batches.
"""

import logging

from packages.graph.client import Neo4jClient
from packages.schemas.core.place import Place

logger = logging.getLogger(__name__)


class PlaceWriter:
    """Batched Neo4j writer for Place entity ingestion.

    Implements GraphWriterPort interface using batched UNWIND operations.
    Ensures atomic writes and high throughput (target ≥20k edges/min).

    Attributes:
        neo4j_client: Neo4j client instance with connection pooling.
        batch_size: Number of rows per UNWIND batch (default 2000).
    """

    def __init__(self, neo4j_client: Neo4jClient, batch_size: int = 2000) -> None:
        """Initialize PlaceWriter with Neo4j client.

        Args:
            neo4j_client: Neo4j client instance (must be connected).
            batch_size: Number of rows per UNWIND batch (default 2000).
        """
        self.neo4j_client = neo4j_client
        self.batch_size = batch_size

        logger.info(f"Initialized PlaceWriter (batch_size={batch_size})")

    def write_places(self, places: list[Place]) -> dict[str, int]:
        """Write Place nodes to Neo4j using batched UNWIND.

        Creates or updates Place nodes with all properties.
        Uses MERGE on unique key (name) for idempotency.

        Args:
            places: List of Place entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total places written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If places list contains invalid data.
            Exception: If Neo4j write operation fails.
        """
        if not places:
            logger.info("No places to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare place parameters (optimized list comprehension)
        try:
            place_params = [
                {
                    "name": p.name,
                    "address": p.address,
                    "coordinates": p.coordinates,
                    "place_type": p.place_type,
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
                for p in places
            ]
        except AttributeError as e:
            logger.error(f"Invalid Place entity in batch: {e}")
            raise ValueError(f"Invalid Place entity: {e}") from e

        # Execute in batches
        try:
            with self.neo4j_client.session() as session:
                for i in range(0, len(place_params), self.batch_size):
                    batch = place_params[i : i + self.batch_size]

                    # Optimized Cypher query with explicit property setting
                    query = """
                    UNWIND $rows AS row
                    MERGE (p:Place {name: row.name})
                    SET p.address = row.address,
                        p.coordinates = row.coordinates,
                        p.place_type = row.place_type,
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
                        f"Wrote place batch {batches_executed}: "
                        f"{len(batch)} rows, "
                        f"counters={summary.counters}"
                    )

            logger.info(f"Wrote {total_written} Place node(s) in {batches_executed} batch(es)")

            return {"total_written": total_written, "batches_executed": batches_executed}

        except Exception as e:
            logger.error(
                f"Failed to write places to Neo4j: {e}",
                extra={"batch_size": self.batch_size, "total_places": len(places)},
            )
            raise


# Export public API
__all__ = ["PlaceWriter"]
