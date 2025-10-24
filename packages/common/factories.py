"""Factory functions for creating fully-wired use cases and dependencies.

Centralizes dependency injection to keep CLI commands and API routes thin.
"""

from collections.abc import Callable

from packages.clients.postgres_document_store import PostgresDocumentStore
from packages.common.config import get_config
from packages.common.db_schema import get_postgres_client
from packages.core.use_cases.ingest_youtube import IngestYouTubeUseCase
from packages.core.use_cases.reprocess import ReprocessUseCase
from packages.ingest.chunker import Chunker
from packages.ingest.embedder import Embedder
from packages.ingest.normalizer import Normalizer
from packages.ingest.readers.youtube import YoutubeReader
from packages.vector.writer import QdrantWriter


def make_reprocess_use_case() -> tuple[ReprocessUseCase, Callable[[], None]]:
    """Create a fully-wired ReprocessUseCase with its dependencies.

    Returns:
        Tuple of (use_case, cleanup_fn) where cleanup_fn must be called
        after use to close database connections.

    Example:
        use_case, cleanup = make_reprocess_use_case()
        try:
            result = use_case.execute(since_date=some_date)
        finally:
            cleanup()
    """
    conn = get_postgres_client()
    document_store = PostgresDocumentStore(conn)
    use_case = ReprocessUseCase(document_store=document_store)

    def cleanup() -> None:
        """Close database connections."""
        conn.close()

    return use_case, cleanup


def make_ingest_youtube_use_case() -> tuple[IngestYouTubeUseCase, Callable[[], None]]:
    """Create a fully-wired IngestYouTubeUseCase with its dependencies.

    Returns:
        Tuple of (use_case, cleanup_fn) where cleanup_fn must be called
        after use to close connections and release resources.

    Example:
        use_case, cleanup = make_ingest_youtube_use_case()
        try:
            result = use_case.execute(urls=video_urls)
        finally:
            cleanup()
    """
    config = get_config()

    # Initialize dependencies
    youtube_reader = YoutubeReader()
    normalizer = Normalizer()
    chunker = Chunker()

    tei_settings = config.tei_config
    embedder = Embedder(
        tei_url=str(tei_settings.url),
        batch_size=tei_settings.batch_size,
        timeout=float(tei_settings.timeout),
    )

    qdrant_writer = QdrantWriter(
        url=config.qdrant_url,
        collection_name=config.collection_name,
    )

    # Create use case
    use_case = IngestYouTubeUseCase(
        youtube_reader=youtube_reader,
        normalizer=normalizer,
        chunker=chunker,
        embedder=embedder,
        qdrant_writer=qdrant_writer,
    )

    def cleanup() -> None:
        """Close connections and release resources."""
        embedder.close()
        qdrant_writer.close()

    return use_case, cleanup
