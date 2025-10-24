"""Ingest Elasticsearch command for Taboot CLI."""

import json
import logging
from typing import Annotated

import typer
from rich.console import Console

from packages.clients.postgres_document_store import PostgresDocumentStore
from packages.common.config import get_config
from packages.common.db_schema import get_postgres_client
from packages.core.use_cases.ingest_elasticsearch import IngestElasticsearchUseCase
from packages.ingest.chunker import Chunker
from packages.ingest.embedder import Embedder
from packages.ingest.normalizer import Normalizer
from packages.ingest.readers.elasticsearch import ElasticsearchReader
from packages.vector.writer import QdrantWriter

console = Console()
logger = logging.getLogger(__name__)

# Default Elasticsearch query to match all documents
DEFAULT_QUERY = '{"match_all": {}}'


def ingest_elasticsearch_command(
    index: Annotated[str, typer.Argument(..., help="Elasticsearch index name")],
    query: Annotated[str, typer.Option("--query", "-q", help="JSON query DSL")] = DEFAULT_QUERY,
    limit: Annotated[
        int | None,
        typer.Option("--limit", "-l", help="Maximum number of documents to ingest"),
    ] = None,
) -> None:
    """Ingest Elasticsearch documents into the knowledge graph.

from __future__ import annotations

    Example:
        uv run apps/cli ingest elasticsearch my-index --limit 100
        uv run apps/cli ingest elasticsearch logs --query '{"match": {"status": "error"}}'
    """
    try:
        config = get_config()

        # Validate Elasticsearch URL is configured
        if not config.elasticsearch_url:
            console.print(
                "[red]✗ Elasticsearch URL not configured. Set ELASTICSEARCH_URL in .env[/red]"
            )
            raise typer.Exit(code=1)

        limit_str = f"limit: {limit}" if limit is not None else "no limit"
        console.print(f"[yellow]Starting Elasticsearch ingestion: {index} ({limit_str})[/yellow]")

        # Parse query JSON
        try:
            query_dict = json.loads(query)
        except json.JSONDecodeError as e:
            console.print(f"[red]✗ Invalid JSON query: {e}[/red]")
            raise typer.Exit(code=1) from e

        # Initialize dependencies
        elasticsearch_reader = ElasticsearchReader(
            endpoint=config.elasticsearch_url,
            index=index,
        )
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
        pg_conn = get_postgres_client()
        document_store = PostgresDocumentStore(pg_conn)

        try:
            # Create and execute use case
            use_case = IngestElasticsearchUseCase(
                elasticsearch_reader=elasticsearch_reader,
                normalizer=normalizer,
                chunker=chunker,
                embedder=embedder,
                qdrant_writer=qdrant_writer,
                document_store=document_store,
                collection_name=config.collection_name,
                index=index,
            )

            # Display progress
            console.print("[yellow]Loading documents from Elasticsearch...[/yellow]")
            stats = use_case.execute(query=query_dict, limit=limit)

            # Display results
            console.print(
                f"[green]✓ Processed {stats['docs_processed']} documents, "
                f"created {stats['chunks_created']} chunks[/green]"
            )
            console.print("[green]✓ Elasticsearch ingestion complete![/green]")

        finally:
            # Ensure all resources are closed
            document_store.close()
            pg_conn.close()

    except ValueError as e:
        console.print(f"[yellow]⚠ {e}[/yellow]")
        raise typer.Exit(code=0) from None
    except Exception:
        logger.exception("Elasticsearch ingestion failed")
        console.print("[red]✗ Elasticsearch ingestion failed[/red]")
        raise typer.Exit(code=1) from None
