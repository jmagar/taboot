"""Ingest YouTube command for Taboot CLI."""

import logging
from contextlib import ExitStack
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

import typer
from llama_index.core import Document
from rich.console import Console

from packages.common.config import get_config
from packages.ingest.chunker import Chunker
from packages.ingest.embedder import Embedder
from packages.ingest.normalizer import Normalizer
from packages.ingest.readers.youtube import YoutubeReader
from packages.schemas.models import Chunk, SourceType
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

        # Initialize resources with ExitStack to ensure cleanup
        with ExitStack() as stack:
            embedder = Embedder(tei_url=config.tei_embedding_url)
            stack.callback(embedder.close)
            qdrant_writer = QdrantWriter(
                url=config.qdrant_url,
                collection_name=config.collection_name,
            )
            stack.callback(qdrant_writer.close)

            console.print("[yellow]Loading transcripts...[/yellow]")
            docs = youtube_reader.load_data(video_urls=urls)
            console.print(f"[green]✓ Loaded {len(docs)} transcripts[/green]")

            console.print("Normalizing and chunking...")
            all_chunks: list[Chunk] = []

            for doc in docs:
                # Normalize HTML to Markdown
                markdown = normalizer.normalize(doc.text)

                # Create normalized Document
                normalized_doc = Document(
                    text=markdown,
                    metadata=doc.metadata.copy() if doc.metadata else {},
                )

                # Chunk the normalized document
                chunk_docs = chunker.chunk_document(normalized_doc)

                # Convert LlamaIndex Documents to Chunk models
                doc_id = uuid4()  # One doc_id per video
                ingested_at = int(datetime.now(UTC).timestamp())
                source_url = doc.metadata.get("video_url", "") if doc.metadata else ""

                for chunk_doc in chunk_docs:
                    # Extract metadata
                    chunk_index = chunk_doc.metadata.get("chunk_index", 0)

                    # Calculate token count (rough estimate: split by whitespace)
                    token_count = len(chunk_doc.text.split())
                    token_count = max(1, min(token_count, 512))  # Clamp to [1, 512]

                    # Create Chunk model
                    chunk = Chunk(
                        chunk_id=uuid4(),
                        doc_id=doc_id,
                        content=chunk_doc.text,
                        section=None,
                        position=chunk_index,
                        token_count=token_count,
                        source_url=source_url,
                        source_type=SourceType.YOUTUBE,
                        ingested_at=ingested_at,
                        tags=None,
                    )
                    all_chunks.append(chunk)

            console.print(f"[green]✓ Created {len(all_chunks)} chunks[/green]")

            console.print("Generating embeddings...")
            embeddings = embedder.embed_texts([chunk.content for chunk in all_chunks])

            console.print("Writing to Qdrant...")
            qdrant_writer.upsert_batch(chunks=all_chunks, embeddings=embeddings)
            console.print("[green]✓ YouTube ingestion complete![/green]")

    except Exception as e:
        logger.exception("YouTube ingestion failed")
        console.print(f"[red]✗ YouTube ingestion failed: {e}[/red]")
        raise typer.Exit(code=1) from e
