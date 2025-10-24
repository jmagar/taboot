"""Ingest GitHub command for Taboot CLI.

Implements the GitHub repository ingestion workflow.
This command is thin - business logic is in the ingestion pipeline.
"""

from __future__ import annotations

import hashlib
import logging
from contextlib import ExitStack
from datetime import UTC, datetime
from typing import Annotated, NoReturn
from uuid import NAMESPACE_URL, uuid4, uuid5

import typer
from llama_index.core import Document
from rich.console import Console

from packages.clients.postgres_document_store import PostgresDocumentStore
from packages.common.config import get_config
from packages.common.db_schema import get_postgres_client
from packages.ingest.chunker import Chunker
from packages.ingest.embedder import Embedder
from packages.ingest.normalizer import Normalizer
from packages.ingest.readers.github import GithubReader
from packages.schemas.models import (
    Chunk,
    ExtractionState,
    SourceType,
)
from packages.schemas.models import (
    Document as DocumentModel,
)
from packages.vector.writer import QdrantWriter

console = Console()
logger = logging.getLogger(__name__)


def _die(message: str) -> NoReturn:
    """Print error and exit with code 1."""
    console.print(message)
    raise typer.Exit(code=1)


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
            _die(
                f"[red]✗ Invalid repository format: {repo}[/red]\n"
                f"[yellow]Expected format: 'owner/repo' (e.g., 'anthropics/claude')[/yellow]"
            )

        # Load config
        config = get_config()

        # Display starting message (use is not None to show explicit 0 limit)
        limit_str = f"limit: {limit}" if limit is not None else "no limit"
        job_id = uuid4()
        console.print(f"[yellow]Starting GitHub ingestion: {repo} ({limit_str})[/yellow]")
        console.print(f"[yellow]Job ID: {job_id}[/yellow]")

        # Create dependencies with proper resource management
        logger.info("Creating ingestion pipeline dependencies")

        # Validate GitHub token is configured
        if not config.github_token:
            _die("[red]✗ GitHub token not configured (GITHUB_TOKEN env var required)[/red]")

        github_reader = GithubReader(
            github_token=config.github_token.get_secret_value(),
        )
        normalizer = Normalizer()
        chunker = Chunker()
        tei_settings = config.tei_config

        # Initialize resources with ExitStack to ensure cleanup
        with ExitStack() as stack:
            embedder = Embedder(
                tei_url=str(tei_settings.url),
                batch_size=tei_settings.batch_size,
                timeout=float(tei_settings.timeout),
            )
            stack.callback(embedder.close)
            qdrant_writer = QdrantWriter(
                url=config.qdrant_url,
                collection_name=config.collection_name,
            )
            stack.callback(qdrant_writer.close)
            pg_conn = get_postgres_client()
            stack.callback(pg_conn.close)
            document_store = PostgresDocumentStore(pg_conn)
            stack.callback(document_store.close)

            # Load documents from GitHub
            console.print(f"[yellow]Loading documents from {repo}...[/yellow]")
            docs: list[Document] = github_reader.load_data(repo=repo, limit=limit)
            console.print(f"[green]✓ Loaded {len(docs)} documents[/green]")

            # Normalize and chunk
            console.print("[yellow]Normalizing and chunking documents...[/yellow]")
            all_chunks: list[Chunk] = []
            now_dt = datetime.now(UTC)

            for doc in docs:
                # Normalize text
                normalized_text = normalizer.normalize(doc.text)
                normalized_doc = Document(text=normalized_text, metadata=doc.metadata)

                # Chunk
                chunk_docs = chunker.chunk_document(normalized_doc)

                # Create deterministic IDs scoped to repo/path to ensure idempotency
                content_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
                file_path = str(doc.metadata.get("path", ""))
                branch = str(doc.metadata.get("branch", "main"))

                # Namespace by repo to prevent collisions
                repo_ns = uuid5(NAMESPACE_URL, f"https://github.com/{repo}")
                name = (
                    f"{branch}:{file_path}:{content_hash}"
                    if file_path
                    else f"{branch}:{content_hash}"
                )
                doc_id = uuid5(repo_ns, name)

                # Construct proper GitHub URL if source_url not available
                source_url = doc.metadata.get("source_url", "")
                if not source_url:
                    sha = (
                        doc.metadata.get("sha")
                        or doc.metadata.get("commit")
                        or doc.metadata.get("commit_sha")
                    )
                    ref = sha or branch
                    if file_path:
                        source_url = f"https://github.com/{repo}/blob/{ref}/{file_path}"
                    else:
                        source_url = f"https://github.com/{repo}"

                # Convert chunks to models
                ingested_at = int(now_dt.timestamp())
                for chunk_doc in chunk_docs:
                    chunk_index = chunk_doc.metadata.get("chunk_index", 0)
                    token_count = max(1, min(len(chunk_doc.text.split()), 512))

                    chunk = Chunk(
                        chunk_id=uuid5(doc_id, str(chunk_index)),
                        doc_id=doc_id,
                        content=chunk_doc.text,
                        section=None,
                        position=chunk_index,
                        token_count=token_count,
                        source_url=source_url,
                        source_type=SourceType.GITHUB,
                        ingested_at=ingested_at,
                        tags=None,
                    )
                    all_chunks.append(chunk)

                # Create Document record for extraction pipeline (reuse same content_hash)
                doc_record = DocumentModel(
                    doc_id=doc_id,
                    source_url=source_url,
                    source_type=SourceType.GITHUB,
                    content_hash=content_hash,
                    ingested_at=now_dt,
                    extraction_state=ExtractionState.PENDING,
                    extraction_version=None,
                    updated_at=now_dt,
                    metadata={
                        "repository": repo,
                        "branch": doc.metadata.get("branch"),
                        "chunk_count": len(chunk_docs),
                    },
                )

                document_store.create(doc_record, normalized_text)

            console.print(f"[green]✓ Created {len(all_chunks)} chunks[/green]")

            # Guard against empty chunks
            if not all_chunks:
                console.print("[yellow]No chunks to embed. Nothing to do.[/yellow]")
                return

            # Embed
            console.print("[yellow]Generating embeddings...[/yellow]")
            embeddings = embedder.embed_texts([chunk.content for chunk in all_chunks])
            console.print(f"[green]✓ Generated {len(embeddings)} embeddings[/green]")

            # Write to Qdrant
            console.print("[yellow]Writing to Qdrant...[/yellow]")
            qdrant_writer.upsert_batch(chunks=all_chunks, embeddings=embeddings)
            console.print(f"[green]✓ Wrote {len(all_chunks)} chunks to Qdrant[/green]")

            console.print("[green]✓ GitHub ingestion complete![/green]")

    except Exception:
        logger.exception("GitHub ingestion failed")
        _die("[red]✗ GitHub ingestion failed[/red]")
