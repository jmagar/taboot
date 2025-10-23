"""Ingest GitHub command for Taboot CLI.

Implements the GitHub repository ingestion workflow.
This command is thin - business logic is in the ingestion pipeline.
"""

import hashlib
import logging
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

import typer
from llama_index.core import Document
from rich.console import Console

from packages.common.config import get_config
from packages.common.db_schema import get_postgres_client
from packages.common.postgres_document_store import PostgresDocumentStore
from packages.ingest.chunker import Chunker
from packages.ingest.embedder import Embedder
from packages.ingest.normalizer import Normalizer
from packages.ingest.readers.github import GithubReader
from packages.schemas.models import (
    Chunk,
    Document as DocumentModel,
    ExtractionState,
    SourceType,
)
from packages.vector.writer import QdrantWriter

console = Console()
logger = logging.getLogger(__name__)


def ingest_github_command(
    repo: Annotated[str, typer.Argument(..., help="Repository in format 'owner/repo'")],
    limit: Annotated[
        int | None, typer.Option("--limit", "-l", help="Maximum number of documents to ingest")
    ] = None,
) -> None:
    """Ingest GitHub repository documentation into the knowledge graph.

    Orchestrates the full ingestion pipeline:
    GithubReader → Normalizer → Chunker → Embedder → QdrantWriter

    Args:
        repo: Repository in format 'owner/repo' (e.g., 'anthropics/claude').
        limit: Optional maximum number of documents to ingest.

    Example:
        uv run apps/cli ingest github anthropics/claude --limit 20

    Expected output:
        ✓ Starting GitHub ingestion: anthropics/claude (limit: 20)
        ✓ Job ID: 123e4567-e89b-12d3-a456-426614174000
        ✓ 18 documents loaded
        ✓ 342 chunks created
        ✓ Duration: 45s

    Raises:
        typer.Exit: Exit with code 1 if ingestion fails.
    """
    try:
        # Validate repo format
        if "/" not in repo or repo.count("/") != 1:
            console.print(
                f"[red]✗ Invalid repository format: {repo}[/red]\n"
                f"[yellow]Expected format: 'owner/repo' (e.g., 'anthropics/claude')[/yellow]"
            )
            raise typer.Exit(code=1)

        # Load config
        config = get_config()

        # Display starting message
        limit_str = f"limit: {limit}" if limit else "no limit"
        console.print(f"[yellow]Starting GitHub ingestion: {repo} ({limit_str})[/yellow]")

        # Create dependencies
        logger.info("Creating ingestion pipeline dependencies")

        github_reader = GithubReader(
            github_token=config.github_token,
        )
        normalizer = Normalizer()
        chunker = Chunker()
        embedder = Embedder(
            tei_url=config.tei_embedding_url,
        )
        qdrant_writer = QdrantWriter(
            url=config.qdrant_url,
            collection_name=config.collection_name,
        )

        # PostgreSQL for document tracking
        pg_conn = get_postgres_client()
        document_store = PostgresDocumentStore(pg_conn)

        # Load documents from GitHub
        console.print(f"[yellow]Loading documents from {repo}...[/yellow]")
        docs = github_reader.load_data(repo=repo, limit=limit)
        console.print(f"[green]✓ Loaded {len(docs)} documents[/green]")

        # Normalize and chunk
        console.print("[yellow]Normalizing and chunking documents...[/yellow]")
        all_chunks: list[Chunk] = []
        ingested_at = int(datetime.now(UTC).timestamp())

        for doc in docs:
            # Normalize text
            normalized_text = normalizer.normalize(doc.text)
            normalized_doc = Document(text=normalized_text, metadata=doc.metadata)

            # Chunk
            chunk_docs = chunker.chunk_document(normalized_doc)

            # Convert to Chunk models
            doc_id = uuid4()
            for chunk_doc in chunk_docs:
                chunk_index = chunk_doc.metadata.get("chunk_index", 0)
                token_count = max(1, min(len(chunk_doc.text.split()), 512))

                chunk = Chunk(
                    chunk_id=uuid4(),
                    doc_id=doc_id,
                    content=chunk_doc.text,
                    section=None,
                    position=chunk_index,
                    token_count=token_count,
                    source_url=doc.metadata.get("source_url", repo),
                    source_type=SourceType.GITHUB,
                    ingested_at=ingested_at,
                    tags=None,
                )
                all_chunks.append(chunk)

            # Create Document record for extraction pipeline
            content_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()

            doc_record = DocumentModel(
                doc_id=doc_id,
                source_url=doc.metadata.get("source_url", repo),
                source_type=SourceType.GITHUB,
                content_hash=content_hash,
                ingested_at=datetime.now(UTC),
                extraction_state=ExtractionState.PENDING,
                extraction_version=None,
                updated_at=datetime.now(UTC),
                metadata={
                    "repository": repo,
                    "branch": doc.metadata.get("branch"),
                    "chunk_count": len(chunk_docs),
                },
            )

            document_store.create(doc_record, normalized_text)

        console.print(f"[green]✓ Created {len(all_chunks)} chunks[/green]")

        # Embed
        console.print("[yellow]Generating embeddings...[/yellow]")
        embeddings = embedder.embed_texts([chunk.content for chunk in all_chunks])
        console.print(f"[green]✓ Generated {len(embeddings)} embeddings[/green]")

        # Write to Qdrant
        console.print("[yellow]Writing to Qdrant...[/yellow]")
        qdrant_writer.upsert_batch(chunks=all_chunks, embeddings=embeddings)
        console.print(f"[green]✓ Wrote {len(all_chunks)} chunks to Qdrant[/green]")

        # Close PostgreSQL connection
        document_store.close()

        console.print("[green]✓ GitHub ingestion complete![/green]")

    except ValueError as e:
        console.print(f"[red]✗ Validation error: {e}[/red]")
        raise typer.Exit(code=1)
    except Exception as e:
        logger.exception(f"GitHub ingestion failed: {e}")
        console.print(f"[red]✗ GitHub ingestion failed: {e}[/red]")
        raise typer.Exit(code=1)
