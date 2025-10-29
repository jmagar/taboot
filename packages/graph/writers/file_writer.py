"""FileWriter - Batched Neo4j writer for File entities.

Implements GraphWriterPort using batched UNWIND operations for high throughput.
Follows the pattern from packages/graph/writers/person_writer.py.

Performance target: ≥20k edges/min with 2k-row UNWIND batches.
"""

import logging

from packages.graph.client import Neo4jClient
from packages.schemas.core.file import File

logger = logging.getLogger(__name__)


class FileWriter:
    """Batched Neo4j writer for File entity ingestion.

    Implements GraphWriterPort interface using batched UNWIND operations.
    Ensures atomic writes and high throughput (target ≥20k edges/min).

    Attributes:
        neo4j_client: Neo4j client instance with connection pooling.
        batch_size: Number of rows per UNWIND batch (default 2000).
    """

    def __init__(self, neo4j_client: Neo4jClient, batch_size: int = 2000) -> None:
        """Initialize FileWriter with Neo4j client.

        Args:
            neo4j_client: Neo4j client instance (must be connected).
            batch_size: Number of rows per UNWIND batch (default 2000).
        """
        self.neo4j_client = neo4j_client
        self.batch_size = batch_size

        logger.info(f"Initialized FileWriter (batch_size={batch_size})")

    def write_files(self, files: list[File]) -> dict[str, int]:
        """Write File nodes to Neo4j using batched UNWIND.

        Creates or updates File nodes with all properties.
        Uses MERGE on unique key (file_id) for idempotency.

        Args:
            files: List of File entities to write.

        Returns:
            dict[str, int]: Statistics with keys:
                - total_written: Total files written
                - batches_executed: Number of batches executed

        Raises:
            ValueError: If files list contains invalid data.
            Exception: If Neo4j write operation fails.
        """
        if not files:
            logger.info("No files to write")
            return {"total_written": 0, "batches_executed": 0}

        total_written = 0
        batches_executed = 0

        # Prepare file parameters (optimized list comprehension)
        try:
            file_params = [
                {
                    "name": f.name,
                    "file_id": f.file_id,
                    "source": f.source,
                    "mime_type": f.mime_type,
                    "size_bytes": f.size_bytes,
                    "url": f.url,
                    "created_at": f.created_at.isoformat(),
                    "updated_at": f.updated_at.isoformat(),
                    "source_timestamp": (
                        f.source_timestamp.isoformat() if f.source_timestamp else None
                    ),
                    "extraction_tier": f.extraction_tier,
                    "extraction_method": f.extraction_method,
                    "confidence": f.confidence,
                    "extractor_version": f.extractor_version,
                }
                for f in files
            ]
        except AttributeError as e:
            logger.error(f"Invalid File entity in batch: {e}")
            raise ValueError(f"Invalid File entity: {e}") from e

        # Execute in batches
        try:
            with self.neo4j_client.session() as session:
                for i in range(0, len(file_params), self.batch_size):
                    batch = file_params[i : i + self.batch_size]

                    # Optimized Cypher query with explicit property setting
                    query = """
                    UNWIND $rows AS row
                    MERGE (f:File {file_id: row.file_id})
                    SET f.name = row.name,
                        f.source = row.source,
                        f.mime_type = row.mime_type,
                        f.size_bytes = row.size_bytes,
                        f.url = row.url,
                        f.created_at = row.created_at,
                        f.updated_at = row.updated_at,
                        f.source_timestamp = row.source_timestamp,
                        f.extraction_tier = row.extraction_tier,
                        f.extraction_method = row.extraction_method,
                        f.confidence = row.confidence,
                        f.extractor_version = row.extractor_version
                    RETURN count(f) AS created_count
                    """

                    result = session.run(query, {"rows": batch})
                    summary = result.consume()

                    total_written += len(batch)
                    batches_executed += 1

                    logger.debug(
                        f"Wrote file batch {batches_executed}: "
                        f"{len(batch)} rows, "
                        f"counters={summary.counters}"
                    )

            logger.info(f"Wrote {total_written} File node(s) in {batches_executed} batch(es)")

            return {"total_written": total_written, "batches_executed": batches_executed}

        except Exception as e:
            logger.error(
                f"Failed to write files to Neo4j: {e}",
                extra={"batch_size": self.batch_size, "total_files": len(files)},
            )
            raise


# Export public API
__all__ = ["FileWriter"]
