"""Ingest Gmail command for Taboot CLI."""

import logging
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
from packages.ingest.readers.gmail import GmailReader
from packages.schemas.models import Chunk, SourceType
from packages.vector.writer import QdrantWriter

console = Console()
logger = logging.getLogger(__name__)

# Error message constant for Gmail credentials validation
GMAIL_CREDENTIALS_ERROR = (
    "Gmail credentials not configured (GMAIL_CREDENTIALS_PATH env var required)"
)


def ingest_gmail_command(
    query: Annotated[str, typer.Argument(..., help="Gmail search query (e.g., 'is:unread')")],
    limit: Annotated[
        int | None, typer.Option("--limit", "-l", help="Maximum number of emails to ingest")
    ] = None,
) -> None:
    """Ingest Gmail messages into the knowledge graph.

from __future__ import annotations

    Example:
        uv run apps/cli ingest gmail "is:unread" --limit 50
    """
    try:
        config = get_config()
        limit_str = f"limit: {limit}" if limit is not None else "no limit"
        console.print(f"[yellow]Starting Gmail ingestion: '{query}' ({limit_str})[/yellow]")

        # Validate credentials
        gmail_creds = getattr(config, "gmail_credentials_path", None)
        if not gmail_creds:
            raise ValueError(GMAIL_CREDENTIALS_ERROR)

        gmail_reader = GmailReader(credentials_path=gmail_creds)
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

        try:
            console.print("[yellow]Loading emails...[/yellow]")
            docs = gmail_reader.load_data(query=query, limit=limit)
            console.print(f"[green]✓ Loaded {len(docs)} emails[/green]")

            console.print("[yellow]Normalizing...[/yellow]")
            # Preserve metadata by wrapping normalized text back into Document
            normalized_docs = [
                Document(text=normalizer.normalize(doc.text), metadata=doc.metadata) for doc in docs
            ]

            console.print("[yellow]Chunking...[/yellow]")
            all_chunks: list[Chunk] = []
            ingested_at = int(datetime.now(UTC).timestamp())
            for doc in normalized_docs:
                # Generate unique doc_id per email
                doc_id = uuid4()
                # Call chunk_document with Document object, not string
                chunk_docs = chunker.chunk_document(doc)
                for i, chunk_doc in enumerate(chunk_docs):
                    # Convert LlamaIndex Document to Pydantic Chunk
                    chunk = Chunk(
                        chunk_id=uuid4(),
                        doc_id=doc_id,
                        content=chunk_doc.text,
                        section=None,
                        position=i,
                        # Approximate token count (actual tokenization may differ)
                        token_count=len(chunk_doc.text.split()),
                        source_url=doc.metadata.get("source_url", ""),
                        source_type=SourceType.GMAIL,
                        ingested_at=ingested_at,
                        tags=None,
                    )
                    all_chunks.append(chunk)

            console.print(f"[green]✓ Created {len(all_chunks)} chunks[/green]")

            console.print("[yellow]Generating embeddings...[/yellow]")
            embeddings = embedder.embed_texts([chunk.content for chunk in all_chunks])

            console.print("[yellow]Writing to Qdrant...[/yellow]")
            qdrant_writer.upsert_batch(chunks=all_chunks, embeddings=embeddings)
            console.print("[green]✓ Gmail ingestion complete![/green]")

        finally:
            # Ensure resources are closed
            embedder.close()
            qdrant_writer.close()

    except Exception as err:
        logger.exception("Gmail ingestion failed")
        console.print(f"[red]✗ Gmail ingestion failed: {err}[/red]")
        raise typer.Exit(code=1) from err
