"""Ingest Gmail command for Taboot CLI."""

import logging
from typing import Annotated

import typer
from rich.console import Console

from packages.common.config import get_config
from packages.ingest.chunker import Chunker
from packages.ingest.embedder import Embedder
from packages.ingest.normalizer import Normalizer
from packages.ingest.readers.gmail import GmailReader
from packages.vector.writer import QdrantWriter

console = Console()
logger = logging.getLogger(__name__)


def ingest_gmail_command(
    query: Annotated[str, typer.Argument(..., help="Gmail search query (e.g., 'is:unread')")],
    limit: Annotated[
        int | None, typer.Option("--limit", "-l", help="Maximum number of emails to ingest")
    ] = None,
) -> None:
    """Ingest Gmail messages into the knowledge graph.

    Example:
        uv run apps/cli ingest gmail "is:unread" --limit 50
    """
    try:
        config = get_config()
        limit_str = f"limit: {limit}" if limit else "no limit"
        console.print(f"[yellow]Starting Gmail ingestion: '{query}' ({limit_str})[/yellow]")

        gmail_reader = GmailReader(credentials_path=config.gmail_credentials_path)
        normalizer = Normalizer()
        chunker = Chunker()
        embedder = Embedder(tei_url=config.tei_embedding_url)
        qdrant_writer = QdrantWriter(
            url=config.qdrant_url,
            collection_name=config.collection_name,
        )

        console.print(f"[yellow]Loading emails...[/yellow]")
        docs = gmail_reader.load_data(query=query, limit=limit)
        console.print(f"[green]✓ Loaded {len(docs)} emails[/green]")

        console.print("[yellow]Normalizing...[/yellow]")
        normalized_docs = [normalizer.normalize(doc.text) for doc in docs]

        console.print("[yellow]Chunking...[/yellow]")
        all_chunks = []
        for norm_doc in normalized_docs:
            all_chunks.extend(chunker.chunk(norm_doc))
        console.print(f"[green]✓ Created {len(all_chunks)} chunks[/green]")

        console.print("[yellow]Generating embeddings...[/yellow]")
        embeddings = embedder.embed_texts([chunk.text for chunk in all_chunks])

        console.print("[yellow]Writing to Qdrant...[/yellow]")
        qdrant_writer.upsert_batch(chunks=all_chunks, embeddings=embeddings)
        console.print(f"[green]✓ Gmail ingestion complete![/green]")

    except Exception as e:
        logger.exception(f"Gmail ingestion failed: {e}")
        console.print(f"[red]✗ Gmail ingestion failed: {e}[/red]")
        raise typer.Exit(code=1)
