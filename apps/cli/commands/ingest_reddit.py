"""Ingest Reddit command for Taboot CLI."""

import logging
from typing import Annotated

import typer
from rich.console import Console

from packages.common.config import get_config
from packages.ingest.chunker import Chunker
from packages.ingest.embedder import Embedder
from packages.ingest.normalizer import Normalizer
from packages.ingest.readers.reddit import RedditReader
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
        limit_str = f"limit: {limit}" if limit else "no limit"
        console.print(f"[yellow]Starting Reddit ingestion: r/{subreddit} ({limit_str})[/yellow]")

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

        # Load, normalize, chunk, embed, write
        console.print(f"[yellow]Loading posts from r/{subreddit}...[/yellow]")
        docs = reddit_reader.load_data(subreddit=subreddit, limit=limit)
        console.print(f"[green]✓ Loaded {len(docs)} posts[/green]")

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
        console.print(f"[green]✓ Reddit ingestion complete![/green]")

    except Exception as e:
        logger.exception(f"Reddit ingestion failed: {e}")
        console.print(f"[red]✗ Reddit ingestion failed: {e}[/red]")
        raise typer.Exit(code=1)
