"""Ingest Elasticsearch command for Taboot CLI."""

import json
import logging
from typing import Annotated

import typer
from rich.console import Console

from packages.common.config import get_config
from packages.ingest.chunker import Chunker
from packages.ingest.embedder import Embedder
from packages.ingest.normalizer import Normalizer
from packages.ingest.readers.elasticsearch import ElasticsearchReader
from packages.vector.writer import QdrantWriter

console = Console()
logger = logging.getLogger(__name__)


def ingest_elasticsearch_command(
    index: Annotated[str, typer.Argument(..., help="Elasticsearch index name")],
    query: Annotated[str, typer.Option("--query", "-q", help="JSON query DSL")] = '{"match_all": {}}',
    limit: Annotated[
        int | None, typer.Option("--limit", "-l", help="Maximum number of documents to ingest")
    ] = None,
) -> None:
    """Ingest Elasticsearch documents into the knowledge graph.

    Example:
        uv run apps/cli ingest elasticsearch my-index --limit 100
        uv run apps/cli ingest elasticsearch logs --query '{"match": {"status": "error"}}'
    """
    try:
        config = get_config()
        limit_str = f"limit: {limit}" if limit else "no limit"
        console.print(f"[yellow]Starting Elasticsearch ingestion: {index} ({limit_str})[/yellow]")

        # Parse query JSON
        try:
            query_dict = json.loads(query)
        except json.JSONDecodeError as e:
            console.print(f"[red]✗ Invalid JSON query: {e}[/red]")
            raise typer.Exit(code=1) from e

        elasticsearch_reader = ElasticsearchReader(
            endpoint=config.elasticsearch_url,
            index=index,
        )
        normalizer = Normalizer()
        chunker = Chunker()
        embedder = Embedder(tei_url=config.tei_embedding_url)
        qdrant_writer = QdrantWriter(
            url=config.qdrant_url,
            collection_name=config.collection_name,
        )

        console.print("[yellow]Loading documents from Elasticsearch...[/yellow]")
        docs = elasticsearch_reader.load_data(query=query_dict, limit=limit)
        console.print(f"[green]✓ Loaded {len(docs)} documents[/green]")

        console.print("Normalizing...")
        normalized_docs = [normalizer.normalize(doc.text) for doc in docs]

        console.print("Chunking...")
        all_chunks = []
        for norm_doc in normalized_docs:
            all_chunks.extend(chunker.chunk(norm_doc))
        console.print(f"[green]✓ Created {len(all_chunks)} chunks[/green]")

        console.print("Generating embeddings...")
        embeddings = embedder.embed_texts([chunk.text for chunk in all_chunks])

        console.print("Writing to Qdrant...")
        qdrant_writer.upsert_batch(chunks=all_chunks, embeddings=embeddings)
        console.print("[green]✓ Elasticsearch ingestion complete![/green]")

    except Exception as e:
        logger.exception("Elasticsearch ingestion failed")
        console.print(f"[red]✗ Elasticsearch ingestion failed: {e}[/red]")
        raise typer.Exit(code=1) from e
