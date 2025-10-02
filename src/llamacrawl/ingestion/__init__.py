"""Document ingestion pipeline with chunking, deduplication, and embedding."""

from llamacrawl.ingestion.chunking import ChunkingStrategy, create_chunking_transformation

__all__ = ["ChunkingStrategy", "create_chunking_transformation"]
