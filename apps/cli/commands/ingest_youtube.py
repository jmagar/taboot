"""Ingest YouTube command for Taboot CLI."""

import logging
from typing import Annotated

import typer
from rich.console import Console

from packages.common.config import get_config
from packages.ingest.chunker import Chunker
from packages.ingest.embedder import Embedder
from packages.ingest.normalizer import Normalizer
from packages.ingest.readers.youtube import YoutubeReader
from packages.vector.writer import QdrantWriter

console = Console()
logger = logging.getLogger(__name__)


def ingest_youtube_command(
    urls: Annotated[list[str], typer.Argument(..., help="YouTube video URLs")],
) -> None:
    """Ingest YouTube video transcripts into the knowledge graph.

    Example:
        uv run apps/cli ingest youtube https://www.youtube.com/watch?v=...
    """
    try:
        config = get_config()
        console.print(f"[yellow]Starting YouTube ingestion: {len(urls)} video(s)[/yellow]")

        youtube_reader = YoutubeReader()
        normalizer = Normalizer()
        chunker = Chunker()
        embedder = Embedder(tei_url=config.tei_embedding_url)
        qdrant_writer = QdrantWriter(
            url=config.qdrant_url,
            collection_name=config.collection_name,
        )

        console.print(f"[yellow]Loading transcripts...[/yellow]")
        docs = youtube_reader.load_data(video_urls=urls)
        console.print(f"[green]✓ Loaded {len(docs)} transcripts[/green]")

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
        console.print(f"[green]✓ YouTube ingestion complete![/green]")

    except Exception as e:
        logger.exception(f"YouTube ingestion failed: {e}")
        console.print(f"[red]✗ YouTube ingestion failed: {e}[/red]")
        raise typer.Exit(code=1)
