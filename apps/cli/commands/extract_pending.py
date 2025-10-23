"""Extract pending command for Taboot CLI.

Implements the extraction workflow using ExtractPendingUseCase:
1. Accept optional --limit parameter
2. Create and configure all dependencies (ExtractionOrchestrator, DocumentStore)
3. Execute ExtractPendingUseCase
4. Display progress and results
5. Handle errors gracefully

This command is thin - all business logic is in packages/core/use_cases/extract_pending.py.
"""

import logging
from typing import Annotated, Any
from uuid import UUID

import redis.asyncio
import typer
from redis.asyncio import Redis
from rich.console import Console

from packages.common.config import get_config
from packages.core.use_cases.extract_pending import ExtractPendingUseCase
from packages.extraction.orchestrator import ExtractionOrchestrator
from packages.extraction.tier_a.parsers import parse_code_blocks, parse_tables
from packages.extraction.tier_a.patterns import EntityPatternMatcher
from packages.extraction.tier_b.window_selector import WindowSelector
from packages.extraction.tier_c.llm_client import TierCLLMClient
from packages.schemas.models import Document, ExtractionState

console = Console()
logger = logging.getLogger(__name__)


class InMemoryDocumentStore:
    """Simple in-memory document store for testing and development.

    Implements the DocumentStore protocol from ExtractPendingUseCase.
    In production, this would be replaced with PostgreSQL implementation.
    """

    def __init__(self) -> None:
        """Initialize in-memory document store."""
        self._documents: dict[UUID, Document] = {}
        self._content: dict[UUID, str] = {}

    def query_pending(self, limit: int | None = None) -> list[Document]:
        """Query documents in PENDING extraction state.

        Args:
            limit: Optional maximum number of documents to return.

        Returns:
            list[Document]: List of documents with extraction_state == PENDING.
        """
        pending = [
            doc for doc in self._documents.values()
            if doc.extraction_state == ExtractionState.PENDING
        ]

        if limit is not None:
            return pending[:limit]
        return pending

    def get_content(self, doc_id: UUID) -> str:
        """Get document text content by doc_id.

        Args:
            doc_id: Document UUID.

        Returns:
            str: Document text content.

        Raises:
            KeyError: If document not found.
        """
        if doc_id not in self._content:
            raise KeyError(f"Document {doc_id} not found")
        return self._content[doc_id]

    def update_document(self, document: Document) -> None:
        """Update document in store.

        Args:
            document: Document instance with updated fields.
        """
        self._documents[document.doc_id] = document


class TierAParser:
    """Wrapper for Tier A parser functions."""

    def parse_code_blocks(self, content: str) -> list[dict[str, Any]]:
        """Parse code blocks from content."""
        return parse_code_blocks(content)

    def parse_tables(self, content: str) -> list[dict[str, Any]]:
        """Parse tables from content."""
        return parse_tables(content)


async def extract_pending_command(
    limit: Annotated[
        int | None,
        typer.Option("--limit", "-l", help="Maximum number of documents to process")
    ] = None,
) -> None:
    """Extract pending documents through multi-tier extraction pipeline.

    Orchestrates the full extraction pipeline:
    DocumentStore → ExtractionOrchestrator (Tier A → B → C) → DocumentStore (update state)

    The extraction pipeline runs three tiers:
        Tier A: Deterministic regex/JSON parsing (≥50 pages/sec)
        Tier B: spaCy NLP entity extraction (≥200 sentences/sec)
        Tier C: LLM-based structured extraction (≤250ms/window median)

    Args:
        limit: Optional maximum number of documents to process.

    Example:
        uv run apps/cli extract pending
        uv run apps/cli extract pending --limit 10

    Expected output:
        Extraction Pipeline
        ─────────────────────
        Processed: 42 documents
        Succeeded: 38 documents
        Failed: 4 documents

    Raises:
        typer.Exit: Exit with code 1 if extraction fails.
    """
    try:
        # Load config
        config = get_config()

        # Display starting message
        limit_str = f"limit: {limit}" if limit else "no limit"
        console.print(f"[yellow]Starting extraction pipeline ({limit_str})[/yellow]")

        # Create dependencies
        logger.info("Creating extraction pipeline dependencies")

        # Redis client for state management
        redis_client: Redis[bytes] = await redis.asyncio.from_url(config.redis_url)

        # Tier A components
        tier_a_parser = TierAParser()
        tier_a_patterns = EntityPatternMatcher()

        # Tier B component
        window_selector = WindowSelector()

        # Tier C component
        # Default to qwen3:4b model
        llm_client = TierCLLMClient(
            model="qwen3:4b",
            redis_client=redis_client,
        )

        # Create extraction orchestrator
        orchestrator = ExtractionOrchestrator(
            tier_a_parser=tier_a_parser,
            tier_a_patterns=tier_a_patterns,
            window_selector=window_selector,
            llm_client=llm_client,
            redis_client=redis_client,
        )

        # Create document store (PostgreSQL)
        from packages.common.db_schema import get_postgres_client
        from packages.common.postgres_document_store import PostgresDocumentStore

        pg_conn = get_postgres_client()
        document_store = PostgresDocumentStore(pg_conn)

        # Create use case
        use_case = ExtractPendingUseCase(
            orchestrator=orchestrator,
            document_store=document_store,
        )

        # Execute extraction
        logger.info("Executing extraction for pending documents")
        summary = await use_case.execute(limit=limit)

        # Close Redis connection
        await redis_client.close()

        # Display results
        console.print("\n[bold cyan]Extraction Pipeline[/bold cyan]")
        console.print("─────────────────────")
        console.print(f"[green]Processed: {summary['processed']} documents[/green]")
        console.print(f"[green]Succeeded: {summary['succeeded']} documents[/green]")

        if summary['failed'] > 0:
            console.print(f"[red]Failed: {summary['failed']} documents[/red]")
        else:
            console.print(f"[green]Failed: {summary['failed']} documents[/green]")

        logger.info(
            f"Extraction complete: processed={summary['processed']}, "
            f"succeeded={summary['succeeded']}, failed={summary['failed']}"
        )

    except typer.Exit:
        # Re-raise typer.Exit to preserve exit code
        raise
    except Exception as e:
        # Catch any other errors and report them
        console.print(f"[red]✗ Extraction failed: {e}[/red]")
        logger.error(f"Extraction failed: {e}", exc_info=True)
        raise typer.Exit(1) from None


# Export public API
__all__ = [
    "extract_pending_command",
    "InMemoryDocumentStore",
]
