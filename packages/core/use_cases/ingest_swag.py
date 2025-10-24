"""IngestSwagUseCase - Core orchestration for SWAG config ingestion.

Orchestrates the SWAG reverse proxy config ingestion pipeline:
SwagReader → GraphWriter (batched UNWIND)

Per CLAUDE.md architecture: Core orchestrates, adapters implement.
This use-case depends only on ports (GraphWriterPort) and schemas.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from packages.core.ports.graph_writer import GraphWriterPort
from packages.ingest.readers.swag import SwagReader, SwagReaderError

logger = logging.getLogger(__name__)


class IngestSwagError(Exception):
    """Exception raised when SWAG ingestion fails."""

    pass


class IngestSwagUseCase:
    """Use case for ingesting SWAG reverse proxy config into Neo4j graph.

    Orchestrates the full ingestion pipeline with error handling.
    NO framework dependencies - only imports from adapter packages and ports.

    Attributes:
        swag_reader: SwagReader adapter for parsing nginx configs.
        graph_writer: GraphWriterPort implementation for Neo4j writes.
    """

    def __init__(
        self,
        swag_reader: SwagReader,
        graph_writer: GraphWriterPort,
    ) -> None:
        """Initialize IngestSwagUseCase with dependencies.

        Args:
            swag_reader: SwagReader instance for parsing.
            graph_writer: GraphWriterPort implementation for graph writes.
        """
        self.swag_reader = swag_reader
        self.graph_writer = graph_writer

        logger.info("Initialized IngestSwagUseCase")

    def execute(self, config_path: str) -> dict[str, Any]:
        """Execute the full SWAG config ingestion pipeline.

        Pipeline flow:
        1. Validate config path exists
        2. SwagReader.parse_file(config_path) → ParsedConfig
        3. GraphWriter.write_proxies(proxies) → stats
        4. GraphWriter.write_routes(proxy_name, routes) → stats
        5. Return summary statistics

        Args:
            config_path: Path to nginx config file or directory.

        Returns:
            dict[str, Any]: Summary with keys:
                - proxies_written: int
                - routes_written: int
                - parse_stats: dict (proxy count, route count)
                - write_stats: dict (batches executed, etc.)

        Raises:
            IngestSwagError: If ingestion fails at any stage.
            ValueError: If config_path is invalid.
        """
        try:
            # Step 1: Validate config path
            path = Path(config_path)
            if not path.exists():
                raise ValueError(f"Config file not found: {config_path}")

            logger.info(f"Starting SWAG config ingestion: {config_path}")

            # Step 2: Parse config file
            logger.info(f"Parsing config file: {config_path}")
            parsed = self.swag_reader.parse_file(str(config_path))

            proxies = parsed["proxies"]
            routes = parsed["routes"]

            logger.info(f"Parsed {len(proxies)} proxy(ies) and {len(routes)} route(s)")

            # Early exit for empty config
            if not proxies and not routes:
                logger.info("No proxies or routes to write")
                return {
                    "proxies_written": 0,
                    "routes_written": 0,
                    "parse_stats": {"proxy_count": 0, "route_count": 0},
                    "write_stats": {},
                }

            # Step 3: Write Proxy nodes (batched)
            logger.info(f"Writing {len(proxies)} Proxy node(s) to Neo4j")
            proxy_stats = self.graph_writer.write_proxies(proxies)
            logger.info(f"Wrote Proxy nodes: {proxy_stats}")

            # Step 4: Write ROUTES_TO relationships (batched)
            # Extract proxy name from first proxy (SwagReader guarantees single proxy)
            proxy_name = proxies[0].name if proxies else "swag"

            logger.info(f"Writing {len(routes)} ROUTES_TO relationship(s) to Neo4j")
            route_payloads = [dict(route) for route in routes]
            route_stats = self.graph_writer.write_routes(proxy_name, route_payloads)
            logger.info(f"Wrote ROUTES_TO relationships: {route_stats}")

            # Step 5: Return summary
            summary = {
                "proxies_written": proxy_stats.get("total_written", len(proxies)),
                "routes_written": route_stats.get("total_written", len(routes)),
                "parse_stats": {
                    "proxy_count": len(proxies),
                    "route_count": len(routes),
                },
                "write_stats": {
                    "proxy_batches": proxy_stats.get("batches_executed", 0),
                    "route_batches": route_stats.get("batches_executed", 0),
                },
            }

            logger.info(f"SWAG config ingestion completed successfully: {summary}")
            return summary

        except ValueError:
            # Re-raise validation errors
            raise
        except SwagReaderError as e:
            # Handle SwagReader-specific errors
            logger.error(f"SWAG config parsing failed: {e}", exc_info=True)
            raise IngestSwagError(f"Failed to parse SWAG config: {e}") from e
        except Exception as e:
            # Unexpected errors - preserve full context
            logger.exception(f"Unexpected error during SWAG ingestion: {e}")
            raise IngestSwagError(f"SWAG ingestion failed: {e}") from e


# Export public API
__all__ = ["IngestSwagUseCase", "IngestSwagError"]
