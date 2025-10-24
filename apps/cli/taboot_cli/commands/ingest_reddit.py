"""Ingest Reddit command for Taboot CLI."""

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
from packages.ingest.readers.reddit import RedditReader
from packages.schemas.models import Chunk, SourceType
from packages.vector.writer import QdrantWriter

console = Console()
logger = logging.getLogger(__name__)


def ingest_reddit_command(
    subreddit: Annotated[str, typer.Argument(..., help="Subreddit name (e.g., 'python')")],
    limit: Annotated[
        int | None, typer.Option("--limit", "-l", help="Maximum number of posts to ingest")
    ] = None,
) -> None:
    """Ingest Reddit posts and comments into the knowledge graph.

    Example:
        uv run apps/cli ingest reddit python --limit 20
    """
    try:
        config = get_config()
        limit_str = f"limit: {limit}" if limit is not None else "no limit"
        console.print(
            f"[yellow]Starting Reddit ingestion: r/{subreddit} ({limit_str})[/yellow]"
        )

        # Validate credentials
        if not config.reddit_client_id:
            raise ValueError(
                "Reddit client ID not configured (REDDIT_CLIENT_ID env var required)"
            )
        if not config.reddit_client_secret:
            raise ValueError(
                "Reddit client secret not configured (REDDIT_CLIENT_SECRET env var required)"
            )
        if not config.reddit_user_agent:
            raise ValueError(
                "Reddit user agent not configured (REDDIT_USER_AGENT env var required)"
            )

        reddit_reader = RedditReader(
            client_id=config.reddit_client_id,
            client_secret=config.reddit_client_secret,
            user_agent=config.reddit_user_agent,
        )
        normalizer = Normalizer()
        chunker = Chunker()
        embedder = Embedder(tei_url=config.tei_embedding_url)
        qdrant_writer = QdrantWriter(
            url=config.qdrant_url,
            collection_name=config.collection_name,
        )

        try:
            # Load, normalize, chunk, embed, write
            console.print(f"[yellow]Loading posts from r/{subreddit}...[/yellow]")
            docs = reddit_reader.load_data(subreddit=subreddit, limit=limit)
            console.print(f"[green]✓ Loaded {len(docs)} posts[/green]")

            console.print("[yellow]Normalizing...[/yellow]")
            # Preserve metadata by wrapping normalized text back into Document
            normalized_docs = [
                Document(text=normalizer.normalize(doc.text), metadata=doc.metadata)
                for doc in docs
            ]

            console.print("[yellow]Chunking...[/yellow]")
            all_chunks: list[Chunk] = []
            doc_id = uuid4()
            ingested_at = int(datetime.now(UTC).timestamp())
            for doc in normalized_docs:
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
                        token_count=len(chunk_doc.text.split()),
                        source_url=doc.metadata.get("source_url", ""),
                        source_type=SourceType.REDDIT,
                        ingested_at=ingested_at,
                        tags=None,
                    )
                    all_chunks.append(chunk)

            console.print(f"[green]✓ Created {len(all_chunks)} chunks[/green]")

            console.print("[yellow]Generating embeddings...[/yellow]")
            embeddings = embedder.embed_texts([chunk.content for chunk in all_chunks])

            console.print("[yellow]Writing to Qdrant...[/yellow]")
            qdrant_writer.upsert_batch(chunks=all_chunks, embeddings=embeddings)
            console.print("[green]✓ Reddit ingestion complete![/green]")

        finally:
            # Ensure resources are closed
            embedder.close()
            qdrant_writer.close()

    except Exception as e:
        logger.exception("Reddit ingestion failed")
        console.print(f"[red]✗ Reddit ingestion failed: {e}[/red]")
        raise typer.Exit(code=1) from e
