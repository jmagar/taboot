"""OrganizationWriter - Batched Neo4j writer for Organization entities.

Implements GraphWriterPort using batched UNWIND operations for high throughput.
Follows the pattern from packages/graph/writers/person_writer.py.

Performance target: ≥20k edges/min with 2k-row UNWIND batches.
"""

import logging

from packages.graph.client import Neo4jClient
from packages.schemas.core.organization import Organization

logger = logging.getLogger(__name__)


class OrganizationWriter:
    """Batched Neo4j writer for Organization entity ingestion.

    Implements GraphWriterPort interface using batched UNWIND operations.
    Ensures atomic writes and high throughput (target ≥20k edges/min).

    Attributes:
        neo4j_client: Neo4j client instance with connection pooling.
        batch_size: Number of rows per UNWIND batch (default 2000).
    """

    def __init__(self, neo4j_client: Neo4jClient, batch_size: int = 2000) -> None:
        """Initialize OrganizationWriter with Neo4j client.

        Args:
            neo4j_client: Neo4j client instance (must be connected).
            batch_size: Number of rows per UNWIND batch (default 2000).
        """
        self.neo4j_client = neo4j_client
        self.batch_size = batch_size

        logger.info(f"Initialized OrganizationWriter (batch_size={batch_size})")

    def write_organizations(self, organizations: list[Organization]) -> dict[str, int]:
        """Write Organization nodes to Neo4j using batched UNWIND.

        Creates or updates Organization nodes with all properties.
        Uses MERGE on unique key (name) for idempotency.

        Args:
            organizations: List of Organization entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total organizations written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If organizations list contains invalid data.
            Exception: If Neo4j write operation fails.
        """
        if not organizations:
            logger.info("No organizations to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare organization parameters (optimized list comprehension)
        try:
            org_params = [
                {
                    "name": o.name,
                    "industry": o.industry,
                    "size": o.size,
                    "website": o.website,
                    "description": o.description,
                    "created_at": o.created_at.isoformat(),
                    "updated_at": o.updated_at.isoformat(),
                    "source_timestamp": (
                        o.source_timestamp.isoformat() if o.source_timestamp else None
                    ),
                    "extraction_tier": o.extraction_tier,
                    "extraction_method": o.extraction_method,
                    "confidence": o.confidence,
                    "extractor_version": o.extractor_version,
                }
                for o in organizations
            ]
        except AttributeError as e:
            logger.error(f"Invalid Organization entity in batch: {e}")
            raise ValueError(f"Invalid Organization entity: {e}") from e

        # Execute in batches
        try:
            with self.neo4j_client.session() as session:
                for i in range(0, len(org_params), self.batch_size):
                    batch = org_params[i : i + self.batch_size]

                    # Optimized Cypher query with explicit property setting
                    query = """
                    UNWIND $rows AS row
                    MERGE (o:Organization {name: row.name})
                    SET o.industry = row.industry,
                        o.size = row.size,
                        o.website = row.website,
                        o.description = row.description,
                        o.created_at = row.created_at,
                        o.updated_at = row.updated_at,
                        o.source_timestamp = row.source_timestamp,
                        o.extraction_tier = row.extraction_tier,
                        o.extraction_method = row.extraction_method,
                        o.confidence = row.confidence,
                        o.extractor_version = row.extractor_version
                    RETURN count(o) AS created_count
                    """

                    result = session.run(query, {"rows": batch})
                    summary = result.consume()

                    total_written += len(batch)
                    batches_executed += 1

                    logger.debug(
                        f"Wrote organization batch {batches_executed}: "
                        f"{len(batch)} rows, "
                        f"counters={summary.counters}"
                    )

            logger.info(
                f"Wrote {total_written} Organization node(s) in {batches_executed} batch(es)"
            )

            return {"total_written": total_written, "batches_executed": batches_executed}

        except Exception as e:
            logger.error(
                f"Failed to write organizations to Neo4j: {e}",
                extra={"batch_size": self.batch_size, "total_organizations": len(organizations)},
            )
            raise


# Export public API
__all__ = ["OrganizationWriter"]
